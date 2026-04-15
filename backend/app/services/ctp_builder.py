"""
CTP Builder - Clusters stance-classified snippets into Creative Target Personas.
Groups by General Stance (worldview), enriches each cluster with LLM-generated
CTP Name, Core Insights, Pain Points, Barriers/Objections, and Kill Signals.
"""

import asyncio
from collections import defaultdict, Counter
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import json

from .llm.client import get_llm_client
from .llm.ctp_prompts import CTP_REFINEMENT_PROMPT, HYPOTHESIS_GENERATION_PROMPT


@dataclass
class CreativeTargetPersona:
    """A Creative Target Persona built from stance-clustered review data."""
    ctp_id: str
    ctp_name: str  # Brand-agnostic archetype label
    general_stance: str  # Stance key
    core_insight_general: str  # CD6: brand-agnostic first-person belief
    core_insight_product_anchored: str  # Near-verbatim from reviews
    pain_points: List[Dict[str, Any]]  # [{pain_point, frequency, sources}]
    weight: int  # 1-10 based on review volume
    review_percentage: float  # % of total reviews
    barriers_objections: List[Dict[str, Any]]  # Up to 4 B/O prompts
    kill_signals: Dict[str, List[str]]  # {existence, engagement, conversion}
    snippet_count: int
    representative_snippets: List[Dict[str, Any]]
    top_language_cues: List[str]
    source_distribution: Dict[str, int]
    outcome_distribution: Dict[str, int]
    proof_type_distribution: Dict[str, int]
    trigger_distribution: Dict[str, int]
    blocker_distribution: Dict[str, int]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CTPBuilder:
    """
    Builds Creative Target Personas from stance-classified VoC snippets.

    Core mechanism: Groups snippets by general_stance, then enriches each
    group with LLM-generated persona attributes.
    """

    def __init__(self):
        self.llm = get_llm_client()
        self.min_cluster_size = 2  # Minimum snippets to form a CTP
        self.max_representative_snippets = 5
        self.max_language_cues = 15

    def cluster_by_stance(
        self,
        classified_snippets: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group snippets by general_stance."""
        clusters = defaultdict(list)

        for snippet in classified_snippets:
            stance = snippet.get("general_stance")
            if not stance or stance == "unknown":
                continue
            clusters[stance].append(snippet)

        return dict(clusters)

    async def build_ctps(
        self,
        classified_snippets: List[Dict[str, Any]],
        brand_name: str,
        existing_pain_points: List[str] = None
    ) -> List[CreativeTargetPersona]:
        """
        Build CTPs from stance-classified snippets.

        Args:
            classified_snippets: Snippets with general_stance already set
            brand_name: For LLM context
            existing_pain_points: Pain points from the insights generation

        Returns:
            List of CreativeTargetPersona sorted by weight (highest first)
        """
        clusters = self.cluster_by_stance(classified_snippets)

        if not clusters:
            return []

        total_classified = sum(len(v) for v in clusters.values())

        # Handle small clusters: merge into closest stance or discard
        valid_clusters = {}
        overflow_snippets = []

        for stance, snippets in clusters.items():
            if len(snippets) >= self.min_cluster_size:
                valid_clusters[stance] = snippets
            else:
                overflow_snippets.extend(snippets)

        # If overflow snippets exist, try to merge into the largest cluster
        if overflow_snippets and valid_clusters:
            largest_stance = max(valid_clusters, key=lambda k: len(valid_clusters[k]))
            valid_clusters[largest_stance].extend(overflow_snippets)

        if not valid_clusters:
            # All clusters too small — combine everything into one CTP
            all_snippets = []
            for snippets in clusters.values():
                all_snippets.extend(snippets)
            if all_snippets:
                most_common_stance = Counter(
                    s.get("general_stance", "unknown") for s in all_snippets
                ).most_common(1)[0][0]
                valid_clusters[most_common_stance] = all_snippets

        # Build each CTP with LLM enrichment
        ctps = []
        ctp_num = 0

        for stance, snippets in sorted(valid_clusters.items(), key=lambda x: len(x[1]), reverse=True):
            ctp_num += 1
            percentage = (len(snippets) / total_classified * 100) if total_classified > 0 else 0

            print(f"    [CTP] Building CTP-{ctp_num:02d} for stance '{stance}' ({len(snippets)} snippets, {percentage:.0f}%)...")

            # Gather stats from this cluster
            stats = self._gather_cluster_stats(snippets)

            # LLM refinement call
            try:
                enriched = await asyncio.wait_for(
                    self._enrich_ctp(
                        stance=stance,
                        snippets=snippets,
                        stats=stats,
                        brand_name=brand_name,
                        existing_pain_points=existing_pain_points or [],
                        review_percentage=percentage
                    ),
                    timeout=60.0
                )
            except (asyncio.TimeoutError, Exception) as e:
                print(f"    [CTP] LLM enrichment failed for {stance}: {str(e)[:50]}, using defaults")
                enriched = self._default_enrichment(stance, snippets, stats)

            # Select representative snippets
            representative = self._select_representative(snippets)

            weight = max(1, min(10, round(percentage / 10)))

            ctp = CreativeTargetPersona(
                ctp_id=f"CTP-{ctp_num:02d}",
                ctp_name=enriched.get("ctp_name", stance.replace("_", " ").title()),
                general_stance=stance,
                core_insight_general=enriched.get("core_insight_general_stance", ""),
                core_insight_product_anchored=enriched.get("core_insight_product_anchored", ""),
                pain_points=enriched.get("pain_points", []),
                weight=weight,
                review_percentage=round(percentage, 1),
                barriers_objections=enriched.get("barriers_objections", [])[:4],
                kill_signals=enriched.get("kill_signals", {"existence": [], "engagement": [], "conversion": []}),
                snippet_count=len(snippets),
                representative_snippets=representative,
                top_language_cues=stats["top_language_cues"],
                source_distribution=stats["source_distribution"],
                outcome_distribution=stats["outcome_distribution"],
                proof_type_distribution=stats["proof_type_distribution"],
                trigger_distribution=stats["trigger_distribution"],
                blocker_distribution=stats["blocker_distribution"]
            )
            ctps.append(ctp)

        # Sort by weight descending
        ctps.sort(key=lambda c: c.weight, reverse=True)

        return ctps

    def _gather_cluster_stats(self, snippets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Gather stats from a cluster of snippets."""
        sources = Counter()
        outcomes = Counter()
        proofs = Counter()
        triggers = Counter()
        blockers = Counter()
        all_cues = []

        for s in snippets:
            classification = s.get("classification", s)
            sources[s.get("source_type", "unknown")] += 1
            outcome = classification.get("desired_outcome_level") or s.get("desired_outcome_level", "")
            if outcome:
                outcomes[outcome] += 1
            proof = classification.get("proof_type_trusted") or s.get("proof_type_trusted", "")
            if proof:
                proofs[proof] += 1
            trigger = classification.get("primary_trigger") or s.get("primary_trigger", "")
            if trigger:
                triggers[trigger] += 1
            blocker = classification.get("blocker_type") or s.get("blocker_type", "")
            if blocker:
                blockers[blocker] += 1
            cues = classification.get("language_cues") or s.get("language_cues") or []
            if isinstance(cues, list):
                all_cues.extend(cues)

        cue_counts = Counter(all_cues)
        top_cues = [c for c, _ in cue_counts.most_common(self.max_language_cues)]

        return {
            "source_distribution": dict(sources),
            "outcome_distribution": dict(outcomes),
            "proof_type_distribution": dict(proofs),
            "trigger_distribution": dict(triggers),
            "blocker_distribution": dict(blockers),
            "top_language_cues": top_cues
        }

    async def _enrich_ctp(
        self,
        stance: str,
        snippets: List[Dict[str, Any]],
        stats: Dict[str, Any],
        brand_name: str,
        existing_pain_points: List[str],
        review_percentage: float
    ) -> Dict[str, Any]:
        """Use LLM to generate CTP name, core insights, barriers, kill signals."""
        # Pick best snippets for the prompt
        best_snippets = self._select_representative(snippets, max_count=8)
        snippets_text = ""
        for i, s in enumerate(best_snippets, 1):
            content = s.get("content", "")[:300]
            source = s.get("source_type", "")
            snippets_text += f'{i}. "{content}" — ({source})\n'

        pain_points_text = "\n".join(f"- {p}" for p in existing_pain_points[:10]) if existing_pain_points else "(none available)"

        prompt = CTP_REFINEMENT_PROMPT.format(
            brand_name=brand_name,
            stance_key=stance,
            stance_label=stance.replace("_", " ").title(),
            snippet_count=len(snippets),
            review_percentage=review_percentage,
            snippets_text=snippets_text,
            pain_points_text=pain_points_text,
            top_triggers=", ".join(f"{k}: {v}" for k, v in stats["trigger_distribution"].items()),
            top_blockers=", ".join(f"{k}: {v}" for k, v in stats["blocker_distribution"].items()),
            outcome_distribution=", ".join(f"{k}: {v}" for k, v in stats["outcome_distribution"].items()),
            proof_distribution=", ".join(f"{k}: {v}" for k, v in stats["proof_type_distribution"].items()),
            top_language_cues=", ".join(stats["top_language_cues"][:10])
        )

        result = await self.llm.complete_json(prompt=prompt, temperature=0.4)
        if result and isinstance(result, dict):
            return result
        return {}

    def _default_enrichment(
        self,
        stance: str,
        snippets: List[Dict[str, Any]],
        stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fallback enrichment when LLM fails."""
        # Use stance_label and stance_belief from the first snippet's classification
        label = stance.replace("_", " ").title()
        belief = ""
        product_quote = ""

        for s in snippets:
            sc = s.get("stance_classification", {})
            if sc.get("stance_label"):
                label = sc["stance_label"]
            if sc.get("stance_belief") and not belief:
                belief = sc["stance_belief"]
            if s.get("content") and not product_quote:
                product_quote = s["content"][:200]

        return {
            "ctp_name": label,
            "core_insight_general_stance": belief,
            "core_insight_product_anchored": product_quote,
            "pain_points": [],
            "barriers_objections": [],
            "kill_signals": {"existence": [], "engagement": [], "conversion": []}
        }

    def _select_representative(
        self,
        snippets: List[Dict[str, Any]],
        max_count: int = None
    ) -> List[Dict[str, Any]]:
        """Select representative snippets, prioritizing those with URLs and high confidence."""
        max_count = max_count or self.max_representative_snippets
        scored = []
        for s in snippets:
            score = 0
            if s.get("source_url"):
                score += 2
            sc = s.get("stance_classification", s)
            score += sc.get("stance_confidence", 0.5)
            # Prefer longer content
            content_len = len(s.get("content", ""))
            if content_len > 100:
                score += 1
            scored.append((score, s))

        scored.sort(key=lambda x: x[0], reverse=True)

        result = []
        for _, s in scored[:max_count]:
            result.append({
                "content": (s.get("content") or "")[:300],
                "source_type": s.get("source_type", "unknown"),
                "source_url": s.get("source_url", ""),
                "sentiment": s.get("sentiment", ""),
                "sentiment_score": s.get("sentiment_score"),
                "general_stance": s.get("general_stance", ""),
                "stance_belief": s.get("stance_classification", {}).get("stance_belief", ""),
                "language_cues": (s.get("classification", {}).get("language_cues") or
                                  s.get("language_cues") or [])[:5]
            })
        return result

    async def generate_hypothesis(
        self,
        ctp: CreativeTargetPersona,
        brand_name: str,
        sector: str,
        vertical: str,
        ad_library_data: Optional[Dict[str, Any]] = None,
        ad_creative_patterns: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate the hypothesis layer for a single CTP."""
        # Build ad library summary
        ad_summary = "(no ad library data available)"
        if ad_library_data or ad_creative_patterns:
            parts = []
            if ad_creative_patterns and isinstance(ad_creative_patterns, dict):
                for k, v in ad_creative_patterns.items():
                    if isinstance(v, list) and v:
                        parts.append(f"- {k}: {', '.join(str(x)[:50] for x in v[:5])}")
                    elif isinstance(v, dict):
                        parts.append(f"- {k}: {json.dumps(v)[:200]}")
                    elif v:
                        parts.append(f"- {k}: {str(v)[:100]}")
            if ad_library_data and isinstance(ad_library_data, list):
                parts.append(f"- Total ads analyzed: {len(ad_library_data)}")
            ad_summary = "\n".join(parts) if parts else "(patterns available but empty)"

        pain_points_text = "\n".join(
            f"- {p.get('pain_point', p)} (freq: {p.get('frequency', '?')})"
            for p in (ctp.pain_points or [])
        ) or "(none)"

        barriers_text = "\n".join(
            f"- [{b.get('type', '?')}] {b.get('prompt', b)}"
            for b in (ctp.barriers_objections or [])
        ) or "(none)"

        ks = ctp.kill_signals or {}
        kill_signals_text = (
            f"Existence: {', '.join(ks.get('existence', []))}\n"
            f"Engagement: {', '.join(ks.get('engagement', []))}\n"
            f"Conversion: {', '.join(ks.get('conversion', []))}"
        )

        prompt = HYPOTHESIS_GENERATION_PROMPT.format(
            brand_name=brand_name,
            sector=sector or "Unknown",
            vertical=vertical or "Unknown",
            ctp_name=ctp.ctp_name,
            core_insight=ctp.core_insight_general,
            weight=ctp.weight,
            snippet_count=ctp.snippet_count,
            pain_points_text=pain_points_text,
            barriers_text=barriers_text,
            kill_signals_text=kill_signals_text,
            language_cues_text=", ".join(ctp.top_language_cues[:10]),
            ad_library_summary=ad_summary
        )

        try:
            result = await asyncio.wait_for(
                self.llm.complete_json(prompt=prompt, temperature=0.4),
                timeout=60.0
            )
            if result and isinstance(result, dict):
                result["ctp_id"] = ctp.ctp_id
                result["ctp_name"] = ctp.ctp_name
                return result
        except Exception as e:
            print(f"    [CTP] Hypothesis generation failed for {ctp.ctp_name}: {str(e)[:50]}")

        return {"ctp_id": ctp.ctp_id, "ctp_name": ctp.ctp_name, "error": "generation_failed"}


# ── Convenience function ──────────────────────────────────────────────────

async def build_ctps(
    classified_snippets: List[Dict[str, Any]],
    brand_name: str,
    sector: str = "",
    vertical: str = "",
    existing_pain_points: List[str] = None,
    ad_library_data: Any = None,
    ad_creative_patterns: Any = None
) -> Dict[str, Any]:
    """
    Build CTPs and hypothesis layer from stance-classified snippets.

    Returns:
        Dict with:
        - ctps: List of CTP dicts
        - hypothesis: List of hypothesis dicts (one per CTP)
        - stats: Summary statistics
    """
    builder = CTPBuilder()
    ctps = await builder.build_ctps(classified_snippets, brand_name, existing_pain_points)

    if not ctps:
        return {"ctps": [], "hypothesis": [], "stats": {"total_ctps": 0, "total_snippets": 0}}

    # Generate hypothesis layer for each CTP
    hypotheses = []
    for ctp in ctps:
        print(f"    [CTP] Generating hypothesis layer for {ctp.ctp_name}...")
        hyp = await builder.generate_hypothesis(
            ctp=ctp,
            brand_name=brand_name,
            sector=sector,
            vertical=vertical,
            ad_library_data=ad_library_data,
            ad_creative_patterns=ad_creative_patterns
        )
        hypotheses.append(hyp)

    return {
        "ctps": [c.to_dict() for c in ctps],
        "hypothesis": hypotheses,
        "stats": {
            "total_ctps": len(ctps),
            "total_snippets": sum(c.snippet_count for c in ctps),
            "stances_found": [c.general_stance for c in ctps],
            "top_stance": ctps[0].general_stance if ctps else None,
            "top_weight": ctps[0].weight if ctps else 0,
            "weight_distribution": {c.ctp_name: c.weight for c in ctps}
        }
    }
