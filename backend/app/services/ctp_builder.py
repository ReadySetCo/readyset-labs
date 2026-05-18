"""
CTP Builder - Clusters stance-classified snippets into Creative Target Personas.
Groups by General Stance (worldview), enriches each cluster with LLM-generated
CTP Name, Core Insights, Pain Points, Barriers/Objections, and Kill Signals.
"""

import asyncio
from collections import defaultdict, Counter
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict, field

from .llm.client import get_llm_client
from .llm.ctp_prompts import CTP_REFINEMENT_PROMPT, HYPOTHESIS_GENERATION_PROMPT
from .stance_classifier import STANCE_ARCHETYPES, StanceClassifier


@dataclass
class CreativeTargetPersona:
    """A Creative Target Persona built from data-driven archetype discovery.

    Discovery-driven CTPs (post-April 2026 architecture) will fill the
    discovery_* fields and may have multiple stance_tags instead of a single
    general_stance. Stance-clustered fallback CTPs leave discovery_* empty
    and use general_stance as the primary key.
    """
    ctp_id: str
    ctp_name: str  # Brand- and behavior-specific name (NOT a generic archetype)
    general_stance: str  # Abstract stance key (one of 8) — primary key for stance fallback
    core_insight_general: str  # CD6: first-person belief in customer's vocabulary
    core_insight_product_anchored: str  # Near-verbatim from reviews
    pain_points: List[Dict[str, Any]]
    desires: List[Any]  # may be List[str] (legacy) or List[Dict] (deep enrichment)
    recommended_hooks: List[Dict[str, Any]]
    recommended_value_props: List[Dict[str, Any]]
    weight: int  # 1-10 based on review volume
    review_percentage: float
    barriers_objections: List[Dict[str, Any]]
    kill_signals: Dict[str, List[str]]
    snippet_count: int
    representative_snippets: List[Dict[str, Any]]
    top_language_cues: List[str]
    source_distribution: Dict[str, int]
    outcome_distribution: Dict[str, int]
    proof_type_distribution: Dict[str, int]
    trigger_distribution: Dict[str, int]
    blocker_distribution: Dict[str, int]
    # Discovery-driven extensions (April 2026 v2)
    archetype_psychology: str = ""  # 3-5 sentence psychological texture
    behavioral_markers: List[str] = field(default_factory=list)
    decision_factors: List[Dict[str, Any]] = field(default_factory=list)
    vocabulary: List[str] = field(default_factory=list)
    counter_segment: str = ""
    what_makes_them_unique: str = ""
    stance_tags: List[str] = field(default_factory=list)
    frameworks_that_resonate: List[Dict[str, Any]] = field(default_factory=list)
    tone_and_emotion_arc: Dict[str, Any] = field(default_factory=dict)
    ad_creative_gap: str = ""
    anti_patterns: List[str] = field(default_factory=list)
    evidence_quotes: List[str] = field(default_factory=list)
    source: str = "discovery"  # "discovery" | "stance_fallback"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CTPBuilder:
    """
    Builds Creative Target Personas from stance-classified VoC snippets.

    Core mechanism: Groups snippets by general_stance, then enriches each
    group with LLM-generated persona attributes.
    """

    def __init__(self):
        self.llm = get_llm_client(task_type="strategy")
        # Audit (April 2026): the previous thresholds (min=2, no confidence filter,
        # overflow merged into the dominant cluster) caused every brand to emit
        # 7-8 CTPs — one per predefined stance — with the same generic names
        # repeating across brands ("The Skeptic", "The Value Seeker", ...).
        # These thresholds force the system to honestly say "we don't have enough
        # signal for that stance" instead of inflating clusters with noise.
        self.min_cluster_size = 8  # was 10 — relaxed slightly to surface more niche segments
        self.min_review_percentage = 5.0  # in % — under 5% of total is noise
        self.max_ctps = 5  # cap top-N; reject the "8 buckets every time" pattern
        self.min_confidence = 0.6  # drop low-confidence classifications BEFORE clustering
        self.max_representative_snippets = 5
        self.max_language_cues = 15

    def cluster_by_stance(
        self,
        classified_snippets: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group snippets by general_stance, dropping unknown / low-confidence ones."""
        clusters = defaultdict(list)

        for snippet in classified_snippets:
            stance = snippet.get("general_stance")
            if not stance or stance == "unknown":
                continue
            # Defensive normalization in case anything bypassed the classifier path
            if stance not in STANCE_ARCHETYPES:
                stance = StanceClassifier._normalize_stance(stance)
                if stance == "unknown":
                    continue
                snippet["general_stance"] = stance
            confidence = snippet.get("stance_confidence")
            if confidence is not None and confidence < self.min_confidence:
                continue
            clusters[stance].append(snippet)

        return dict(clusters)

    async def build_ctps(
        self,
        classified_snippets: List[Dict[str, Any]],
        brand_name: str,
        existing_pain_points: List[str] = None,
        brand_context_block: str = "",
        hook_pool: Optional[List[str]] = None,
        value_props_pool: Optional[List[str]] = None,
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
        # ── Pre-cluster audit counters ──────────────────────────────────
        total_input = len(classified_snippets)
        dropped_unknown = sum(
            1 for s in classified_snippets
            if not s.get("general_stance") or s.get("general_stance") == "unknown"
        )
        dropped_low_conf = sum(
            1 for s in classified_snippets
            if s.get("general_stance") and s.get("general_stance") != "unknown"
            and (s.get("stance_confidence") is not None and s.get("stance_confidence") < self.min_confidence)
        )

        clusters = self.cluster_by_stance(classified_snippets)

        if not clusters:
            print(
                f"    [CTP] No qualifying clusters. Input={total_input}, "
                f"dropped_unknown={dropped_unknown}, dropped_low_conf={dropped_low_conf}"
            )
            return []

        total_classified = sum(len(v) for v in clusters.values())

        # ── Apply quality thresholds: min_cluster_size AND min_review_percentage ──
        valid_clusters: Dict[str, List[Dict[str, Any]]] = {}
        dropped_clusters: List[Tuple[str, int, str]] = []  # (stance, n, reason)

        for stance, snippets in clusters.items():
            n = len(snippets)
            pct = (n / total_classified * 100) if total_classified else 0
            if n < self.min_cluster_size:
                dropped_clusters.append((stance, n, f"size<{self.min_cluster_size}"))
                continue
            if pct < self.min_review_percentage:
                dropped_clusters.append((stance, n, f"pct<{self.min_review_percentage}%"))
                continue
            valid_clusters[stance] = snippets

        # IMPORTANT: orphan snippets are DISCARDED, not merged into the dominant
        # cluster. The previous merge behavior amplified whichever stance was
        # already biggest (typically skeptic/bio_hacker on review-heavy data),
        # which is precisely why those archetypes appeared in 100% of analyses.
        dropped_snippet_count = sum(n for _, n, _ in dropped_clusters)

        if not valid_clusters:
            print(
                f"    [CTP] No clusters passed thresholds (input={total_input}, "
                f"classified={total_classified}, dropped_unknown={dropped_unknown}, "
                f"dropped_low_conf={dropped_low_conf}, dropped_clusters={dropped_clusters})"
            )
            return []

        # ── Build each CTP with LLM enrichment, capped at max_ctps ──────
        ctps = []
        ctp_num = 0

        # Sort by size desc, then keep only top max_ctps
        ranked = sorted(valid_clusters.items(), key=lambda x: len(x[1]), reverse=True)
        if len(ranked) > self.max_ctps:
            extra = ranked[self.max_ctps:]
            ranked = ranked[:self.max_ctps]
            for stance, snips in extra:
                dropped_clusters.append((stance, len(snips), f"beyond max_ctps={self.max_ctps}"))

        for stance, snippets in ranked:
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
                        review_percentage=percentage,
                        brand_context_block=brand_context_block or "(no brand context available)",
                        hook_pool=hook_pool or [],
                        value_props_pool=value_props_pool or [],
                    ),
                    timeout=60.0
                )
            except (asyncio.TimeoutError, Exception) as e:
                print(f"    [CTP] LLM enrichment failed for {stance}: {str(e)[:50]}, using defaults")
                enriched = self._default_enrichment(stance, snippets, stats)

            # Select representative snippets
            representative = self._select_representative(snippets)

            weight = max(1, min(10, round(percentage / 10)))

            llm_name = (enriched.get("ctp_name") or "").strip()
            if not llm_name or llm_name.lower() in self._GENERIC_LABELS:
                # LLM regressed to a generic archetype name. Tag it so operators
                # see it's a low-quality output rather than silently shipping it.
                if llm_name:
                    print(f"    [CTP] Generic name '{llm_name}' rejected for stance '{stance}'")
                llm_name = f"Unspecific {stance.replace('_', ' ').title()} (review qualitative cues)"

            # Normalize the LLM-generated desires/hooks/value_props to plain lists
            desires_raw = enriched.get("desires") or []
            desires_clean: List[str] = []
            for d in desires_raw:
                if isinstance(d, dict):
                    txt = d.get("desire") or d.get("text") or d.get("value") or ""
                else:
                    txt = str(d)
                txt = txt.strip()
                if txt and txt not in desires_clean:
                    desires_clean.append(txt)

            hooks_raw = enriched.get("recommended_hooks") or []
            hooks_clean: List[Dict[str, Any]] = []
            for h in hooks_raw:
                if isinstance(h, dict):
                    hook_text = (h.get("hook") or h.get("text") or "").strip()
                    if not hook_text:
                        continue
                    hooks_clean.append({
                        "hook": hook_text,
                        "source": h.get("source") or "new_for_this_ctp",
                        "rationale": h.get("rationale") or "",
                    })
                elif isinstance(h, str) and h.strip():
                    hooks_clean.append({"hook": h.strip(), "source": "new_for_this_ctp", "rationale": ""})

            vps_raw = enriched.get("recommended_value_props") or []
            vps_clean: List[Dict[str, Any]] = []
            for v in vps_raw:
                if isinstance(v, dict):
                    vp_text = (v.get("value_prop") or v.get("text") or "").strip()
                    if not vp_text:
                        continue
                    vps_clean.append({
                        "value_prop": vp_text,
                        "source": v.get("source") or "new_for_this_ctp",
                        "rationale": v.get("rationale") or "",
                    })
                elif isinstance(v, str) and v.strip():
                    vps_clean.append({"value_prop": v.strip(), "source": "new_for_this_ctp", "rationale": ""})

            ctp = CreativeTargetPersona(
                ctp_id=f"CTP-{ctp_num:02d}",
                ctp_name=llm_name,
                general_stance=stance,
                core_insight_general=enriched.get("core_insight_general_stance", ""),
                core_insight_product_anchored=enriched.get("core_insight_product_anchored", ""),
                pain_points=enriched.get("pain_points", []),
                desires=desires_clean[:5],
                recommended_hooks=hooks_clean[:5],
                recommended_value_props=vps_clean[:5],
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

        # ── Audit summary: lets us verify the fix is working ────────────
        qualified = [(s, len(snips)) for s, snips in ranked]
        print(
            f"    [CTP] Audit: input={total_input}, classified={total_classified}, "
            f"dropped_unknown={dropped_unknown}, dropped_low_conf={dropped_low_conf}, "
            f"dropped_orphan_snippets={dropped_snippet_count}"
        )
        print(f"    [CTP] Qualified stances: {qualified}")
        if dropped_clusters:
            print(f"    [CTP] Dropped stances: {dropped_clusters}")
        print(f"    [CTP] Final CTPs: {len(ctps)} (cap={self.max_ctps})")

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
        review_percentage: float,
        brand_context_block: str = "(no brand context available)",
        hook_pool: Optional[List[str]] = None,
        value_props_pool: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Use LLM to generate CTP name, core insights, desires, per-CTP hooks/VPs, barriers, kill signals."""
        # Pick best snippets for the prompt
        best_snippets = self._select_representative(snippets, max_count=8)
        snippets_text = ""
        for i, s in enumerate(best_snippets, 1):
            content = s.get("content", "")[:300]
            source = s.get("source_type", "")
            snippets_text += f'{i}. "{content}" — ({source})\n'

        # Render candidate hooks / value props pools for the LLM. Cap each pool
        # so the prompt stays tight; if pools are empty, the LLM will write all
        # 3 hooks/VPs as "new_for_this_ctp" — that's expected.
        hook_pool = hook_pool or []
        value_props_pool = value_props_pool or []
        hook_candidates_text = (
            "\n".join(f"- {h}" for h in hook_pool[:15]) if hook_pool
            else "(no brand hooks library yet — write 3 new hooks grounded in the snippets)"
        )
        vp_candidates_text = (
            "\n".join(f"- {v}" for v in value_props_pool[:15]) if value_props_pool
            else "(no brand value props yet — write 3 new value props grounded in the snippets)"
        )

        pain_points_text = (
            "\n".join(f"- {p}" for p in existing_pain_points[:10])
            if existing_pain_points else "(none available)"
        )

        prompt = CTP_REFINEMENT_PROMPT.format(
            brand_name=brand_name,
            stance_key=stance,
            stance_label=stance.replace("_", " ").title(),
            snippet_count=len(snippets),
            review_percentage=review_percentage,
            snippets_text=snippets_text,
            top_triggers=", ".join(f"{k}: {v}" for k, v in stats["trigger_distribution"].items()) or "(none)",
            top_blockers=", ".join(f"{k}: {v}" for k, v in stats["blocker_distribution"].items()) or "(none)",
            outcome_distribution=", ".join(f"{k}: {v}" for k, v in stats["outcome_distribution"].items()) or "(none)",
            proof_distribution=", ".join(f"{k}: {v}" for k, v in stats["proof_type_distribution"].items()) or "(none)",
            top_language_cues=", ".join(stats["top_language_cues"][:10]) or "(none)",
            pain_points_text=pain_points_text,
            brand_context_block=brand_context_block,
            hook_candidates_text=hook_candidates_text,
            value_prop_candidates_text=vp_candidates_text,
        )

        result = await self.llm.complete_json(prompt=prompt, temperature=0.4)
        if result and isinstance(result, dict):
            return result
        return {}

    async def build_ctps_via_discovery(
        self,
        brand_name: str,
        corpus: Dict[str, Any],
        brand_context_block: str = "",
        hook_pool: Optional[List[str]] = None,
        value_props_pool: Optional[List[str]] = None,
        ad_library_data: Any = None,
    ) -> List[CreativeTargetPersona]:
        """Discovery-driven CTP construction.

        Pipeline:
          1. discover_archetypes — single LLM call with full corpus
          2. for each archetype, deep_enrich_archetype with ALL attributed snippets
          3. assemble CreativeTargetPersona objects with the full enriched output

        Returns [] if discovery yields nothing — the public build_ctps will
        then fall back to stance-based clustering.
        """
        # Stash the brand name so _assemble_ctp_from_discovery can strip
        # mechanical "{brand_name} X" prefixes the LLM may slip into ctp names.
        self._current_brand_name = brand_name

        archetypes = await self.discover_archetypes(corpus, brand_name)
        if not archetypes:
            return []

        # Build a snippet lookup table: index -> snippet dict
        # The corpus.enumerated_snippets is List[(int, dict)] — it was numbered
        # for the discovery prompt; archetype.snippet_indexes references those.
        enumerated = corpus.get("enumerated_snippets") or []
        index_to_snippet: Dict[int, Dict[str, Any]] = {idx: s for idx, s in enumerated}
        total_for_pct = len(enumerated) or 1

        # Cap to max_ctps even if discovery returned more
        if len(archetypes) > self.max_ctps:
            print(f"    [CTP-Discovery] {len(archetypes)} archetypes returned, capping to {self.max_ctps}")
            archetypes = sorted(
                archetypes,
                key=lambda a: -(len(a.get("snippet_indexes") or [])),
            )[:self.max_ctps]

        ads_data = ad_library_data
        ads_summary_for_archetype = self._render_ads_for_archetype  # bound helper

        ctps: List[CreativeTargetPersona] = []
        for ctp_num, arch in enumerate(archetypes, 1):
            indexes = arch.get("snippet_indexes") or []
            attributed = [index_to_snippet[i] for i in indexes if i in index_to_snippet]
            if not attributed:
                print(f"    [CTP-Discovery] Archetype '{arch.get('name')}' has no resolvable snippets, skipping")
                continue

            ads_block = ads_summary_for_archetype(arch, ads_data)

            deep = await self.deep_enrich_archetype(
                archetype=arch,
                attributed_snippets=attributed,
                brand_name=brand_name,
                brand_block=brand_context_block,
                ads_for_archetype_block=ads_block,
                hook_pool=hook_pool,
                value_props_pool=value_props_pool,
            )

            # If deep enrichment failed, still emit a thin CTP from discovery output
            # — it's better than nothing because discovery itself was deep.
            ctp = self._assemble_ctp_from_discovery(
                ctp_num=ctp_num,
                archetype=arch,
                deep=deep,
                attributed_snippets=attributed,
                total_snippets=total_for_pct,
            )
            ctps.append(ctp)

        # Sort by review_percentage (highest first)
        ctps.sort(key=lambda c: c.review_percentage, reverse=True)
        return ctps

    def _render_ads_for_archetype(self, archetype: Dict[str, Any], ad_library_data: Any) -> str:
        """Subset the ad library to ads the archetype's ad_alignment field referenced."""
        from .brand_context import render_ads_block
        alignment = archetype.get("ad_alignment") or []
        if not alignment or ad_library_data is None:
            return "(no ads explicitly aligned with this archetype by discovery)"
        # Resolve ad_library_data to a list
        ads: List[Any] = []
        if isinstance(ad_library_data, dict):
            for k in ("ads", "brand_ads", "items", "results"):
                if isinstance(ad_library_data.get(k), list):
                    ads = ad_library_data[k]
                    break
        elif isinstance(ad_library_data, list):
            ads = ad_library_data
        if not ads:
            return "(ad library empty)"
        subset = []
        for idx in alignment:
            if isinstance(idx, int) and 0 <= idx < len(ads):
                subset.append(ads[idx])
        if not subset:
            return "(no ads matched the archetype's alignment indexes)"
        return render_ads_block(subset, max_ads=len(subset))

    def _assemble_ctp_from_discovery(
        self,
        ctp_num: int,
        archetype: Dict[str, Any],
        deep: Dict[str, Any],
        attributed_snippets: List[Dict[str, Any]],
        total_snippets: int,
    ) -> CreativeTargetPersona:
        """Combine discovery output + deep enrichment output into a CreativeTargetPersona.

        deep takes precedence when present; falls back to discovery values if a
        field is missing (because deep enrichment failed)."""
        # Helper: prefer deep, fallback to archetype, fallback to default
        def pick(deep_key: str, arch_key: str = None, default=None):
            if deep.get(deep_key) is not None:
                return deep[deep_key]
            if arch_key and archetype.get(arch_key) is not None:
                return archetype[arch_key]
            return default

        n_attributed = len(attributed_snippets)
        percentage = (n_attributed / total_snippets * 100) if total_snippets else 0
        weight = max(1, min(10, round(percentage / 10) or 1))

        # Stats from attributed snippets
        stats = self._gather_cluster_stats(attributed_snippets)

        # Stance tags: prefer discovery's list; if empty, use the dominant stance from snippets
        stance_tags = archetype.get("stance_tags") or []
        if isinstance(stance_tags, str):
            stance_tags = [stance_tags]
        if not stance_tags:
            from collections import Counter as _C
            sc = _C(s.get("general_stance") for s in attributed_snippets if s.get("general_stance"))
            stance_tags = [sc.most_common(1)[0][0]] if sc else ["unknown"]

        primary_stance = stance_tags[0] if stance_tags else "unknown"

        # Reject generic names (defensive — the prompt forbids them but trust-but-verify)
        ctp_name = (deep.get("ctp_name") or archetype.get("name") or "").strip()
        # Strip mechanical brand-name prepending: "Phlur Compliment-Chasing X" -> "Compliment-Chasing X"
        # Only strip if the brand name is at the START as a lazy prefix; keep it if it's
        # embedded in a meaningful way (e.g., "Old-Phlur Revival Loyalists" refers to a brand era).
        brand_name_local = getattr(self, "_current_brand_name", "")
        if brand_name_local and ctp_name.lower().startswith(brand_name_local.lower() + " "):
            stripped = ctp_name[len(brand_name_local) + 1:].strip()
            if stripped:
                print(f"    [CTP-Discovery] Stripping mechanical brand prefix: "
                      f"'{ctp_name}' -> '{stripped}'")
                ctp_name = stripped
        if ctp_name.lower() in self._GENERIC_LABELS or not ctp_name:
            print(f"    [CTP-Discovery] Generic/missing name '{ctp_name}' rejected, "
                  f"keeping archetype name: {archetype.get('name')}")
            ctp_name = archetype.get("name") or f"Unspecific Discovery Archetype {ctp_num}"

        return CreativeTargetPersona(
            ctp_id=f"CTP-{ctp_num:02d}",
            ctp_name=ctp_name,
            general_stance=primary_stance,
            core_insight_general=pick("core_insight_general_stance", default=""),
            core_insight_product_anchored=pick("core_insight_product_anchored", default=""),
            pain_points=pick("pain_points", default=[]),
            desires=pick("desires", default=[]),
            recommended_hooks=pick("recommended_hooks", default=[]),
            recommended_value_props=pick("recommended_value_props", default=[]),
            weight=weight,
            review_percentage=round(percentage, 1),
            barriers_objections=(pick("barriers_objections", default=[]) or [])[:6],
            kill_signals=pick("kill_signals", default={"existence": [], "engagement": [], "conversion": []}),
            snippet_count=n_attributed,
            representative_snippets=self._select_representative(attributed_snippets, max_count=8),
            top_language_cues=stats["top_language_cues"],
            source_distribution=stats["source_distribution"],
            outcome_distribution=stats["outcome_distribution"],
            proof_type_distribution=stats["proof_type_distribution"],
            trigger_distribution=stats["trigger_distribution"],
            blocker_distribution=stats["blocker_distribution"],
            # Discovery-driven extensions
            archetype_psychology=archetype.get("psychology", "") or "",
            behavioral_markers=pick("behavioral_markers", "behavioral_markers", []) or [],
            decision_factors=deep.get("decision_factors") or [],
            vocabulary=deep.get("vocabulary") or [],
            counter_segment=archetype.get("counter_segment", "") or "",
            what_makes_them_unique=archetype.get("what_makes_them_unique", "") or "",
            stance_tags=stance_tags,
            frameworks_that_resonate=deep.get("frameworks_that_resonate") or [],
            tone_and_emotion_arc=deep.get("tone_and_emotion_arc") or {},
            ad_creative_gap=deep.get("ad_creative_gap", "") or "",
            anti_patterns=deep.get("anti_patterns") or [],
            evidence_quotes=archetype.get("evidence_quotes") or [],
            source="discovery",
        )

    # ── Discovery-driven archetype pipeline (April 2026 v2) ────────────
    # Replaces forced 8-bucket clustering as the primary path. Stance
    # classification still runs upstream — its output goes into the
    # snippets_block as ONE signal among many, not a structural constraint.

    async def discover_archetypes(
        self,
        corpus: Dict[str, Any],
        brand_name: str,
        timeout: float = 180.0,
    ) -> List[Dict[str, Any]]:
        """Single LLM call: read the full corpus, return emergent archetypes.

        corpus: output of services.brand_context.build_discovery_corpus(...)
                Contains brand_block, snippets_block, ads_block, enumerated_snippets.

        Returns: list of archetype dicts (name, psychology, behavioral_markers,
                 snippet_indexes, evidence_quotes, stance_tags, ad_alignment,
                 estimated_share_pct, counter_segment, what_makes_them_unique).
                 Empty list if discovery fails — caller should fall back.
        """
        from .llm.ctp_prompts import CTP_DISCOVERY_PROMPT
        prompt = CTP_DISCOVERY_PROMPT.format(
            brand_name=brand_name,
            brand_block=corpus.get("brand_block", "(missing)"),
            snippets_block=corpus.get("snippets_block", "(missing)"),
            ads_block=corpus.get("ads_block", "(none)"),
        )
        n_snippets = corpus.get("meta", {}).get("snippet_count", 0)
        approx = corpus.get("meta", {}).get("approx_input_chars", 0)
        print(f"    [CTP-Discovery] Running discovery: {n_snippets} snippets, "
              f"~{approx} input chars (~{approx // 4} tokens)")

        try:
            result = await asyncio.wait_for(
                self.llm.complete_json(prompt=prompt, temperature=0.4),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            print(f"    [CTP-Discovery] TIMEOUT after {timeout}s — falling back")
            return []
        except Exception as e:
            print(f"    [CTP-Discovery] FAILED: {type(e).__name__}: {str(e)[:120]}")
            return []

        if not isinstance(result, dict):
            print(f"    [CTP-Discovery] Bad shape: {type(result).__name__}")
            return []

        archetypes = result.get("archetypes")
        if not isinstance(archetypes, list) or not archetypes:
            print(f"    [CTP-Discovery] No archetypes in response. Keys: {list(result.keys())[:5]}")
            return []

        rationale = result.get("rationale", "")
        if rationale:
            print(f"    [CTP-Discovery] Rationale: {rationale[:200]}")

        # Validate each archetype has the minimum we need
        valid: List[Dict[str, Any]] = []
        for i, arch in enumerate(archetypes):
            if not isinstance(arch, dict):
                continue
            name = (arch.get("name") or "").strip()
            indexes = arch.get("snippet_indexes") or []
            if not name or not isinstance(indexes, list) or len(indexes) < 5:
                print(f"    [CTP-Discovery] Skipping archetype #{i}: name='{name}', n_indexes={len(indexes) if isinstance(indexes, list) else '?'}")
                continue
            valid.append(arch)

        print(f"    [CTP-Discovery] Discovered {len(valid)} valid archetypes "
              f"(of {len(archetypes)} returned):")
        for a in valid:
            print(f"      • {a.get('name')[:60]} — {len(a.get('snippet_indexes', []))} snippets, "
                  f"~{a.get('estimated_share_pct', '?')}%, "
                  f"stances={a.get('stance_tags', [])}")

        return valid

    async def discover_target_personas(
        self,
        corpus: Dict[str, Any],
        brand_name: str,
        existing_ctps: List[Dict[str, Any]],
        timeout: float = 180.0,
    ) -> List[Dict[str, Any]]:
        """Single LLM call: read the full corpus and discover Target Personas.

        Target Personas = prospects (Unaware / Problem-Aware / Solution-Aware in
        Schwartz's framework). NOT customer CTPs — those have already been built.
        Existing CTPs are shown to the prompt so the LLM doesn't duplicate them.

        Returns list of target persona dicts. Empty list on failure.
        """
        from .llm.ctp_prompts import TARGET_PERSONA_DISCOVERY_PROMPT

        # Compact summary of existing CTPs so the LLM doesn't duplicate
        if existing_ctps:
            summary_lines = []
            for c in existing_ctps[:8]:
                name = c.get("ctp_name") or "?"
                psy = (c.get("archetype_psychology") or c.get("core_insight_general") or "")[:120]
                summary_lines.append(f"  - {name}: {psy}")
            existing_summary = "\n".join(summary_lines)
        else:
            existing_summary = "(no CTPs yet — your output should still focus on prospects, not buyers)"

        prompt = TARGET_PERSONA_DISCOVERY_PROMPT.format(
            brand_name=brand_name,
            brand_block=corpus.get("brand_block", "(missing)"),
            snippets_block=corpus.get("snippets_block", "(missing)"),
            ads_block=corpus.get("ads_block", "(none)"),
            existing_ctps_summary=existing_summary,
        )

        approx = len(prompt)
        print(f"    [TargetPersonas] Running discovery: ~{approx // 4} input tokens")

        try:
            result = await asyncio.wait_for(
                self.llm.complete_json(prompt=prompt, temperature=0.4),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            print(f"    [TargetPersonas] TIMEOUT after {timeout}s")
            return []
        except Exception as e:
            print(f"    [TargetPersonas] FAILED: {type(e).__name__}: {str(e)[:120]}")
            return []

        if not isinstance(result, dict):
            print(f"    [TargetPersonas] Bad shape: {type(result).__name__}")
            return []

        personas = result.get("target_personas")
        if not isinstance(personas, list) or not personas:
            print(f"    [TargetPersonas] No personas in response. Keys: {list(result.keys())[:5]}")
            return []

        rationale = result.get("rationale", "")
        if rationale:
            print(f"    [TargetPersonas] Rationale: {rationale[:200]}")

        # Validate
        valid: List[Dict[str, Any]] = []
        for i, p in enumerate(personas):
            if not isinstance(p, dict):
                continue
            name = (p.get("name") or "").strip()
            indexes = p.get("evidence_indexes") or []
            awareness = p.get("awareness_level") or ""
            valid_awareness = awareness in ("Unaware", "Problem Aware", "Solution Aware")
            if not name or not isinstance(indexes, list) or len(indexes) < 3 or not valid_awareness:
                print(f"    [TargetPersonas] Skipping #{i}: name='{name}', "
                      f"awareness='{awareness}', n_indexes={len(indexes) if isinstance(indexes, list) else '?'}")
                continue
            valid.append(p)

        print(f"    [TargetPersonas] Discovered {len(valid)} valid target personas:")
        for p in valid:
            print(f"      • [{p.get('awareness_level'):16}] {p.get('name')[:60]} "
                  f"— {len(p.get('evidence_indexes', []))} snippets, "
                  f"~{p.get('estimated_share_of_addressable_market', '?')}% TAM, "
                  f"acq={p.get('estimated_acquisition_difficulty', '?')}")

        return valid

    async def deep_enrich_archetype(
        self,
        archetype: Dict[str, Any],
        attributed_snippets: List[Dict[str, Any]],
        brand_name: str,
        brand_block: str,
        ads_for_archetype_block: str = "",
        hook_pool: Optional[List[str]] = None,
        value_props_pool: Optional[List[str]] = None,
        timeout: float = 120.0,
    ) -> Dict[str, Any]:
        """Single LLM call to construct a deep CTP from a discovered archetype.

        Sends ALL attributed snippets (not just 8) plus the brand context.
        Returns the full deep-enrichment dict from the LLM, or {} on failure.
        """
        from .llm.ctp_prompts import CTP_DEEP_ENRICHMENT_PROMPT

        # Render attributed snippets for the LLM (using same format as discovery)
        from .brand_context import render_snippets_block
        enumerated = list(enumerate(attributed_snippets))
        snippets_block = render_snippets_block(enumerated)

        hook_pool = hook_pool or []
        value_props_pool = value_props_pool or []
        hook_candidates_text = (
            "\n".join(f"- {h}" for h in hook_pool[:20]) if hook_pool
            else "(no brand hooks library — write 3-5 new hooks grounded in the snippets)"
        )
        vp_candidates_text = (
            "\n".join(f"- {v}" for v in value_props_pool[:20]) if value_props_pool
            else "(no brand value props — write 3-5 new value props grounded in the snippets)"
        )

        prompt = CTP_DEEP_ENRICHMENT_PROMPT.format(
            brand_name=brand_name,
            archetype_name=archetype.get("name", ""),
            archetype_psychology=archetype.get("psychology", ""),
            archetype_behavioral_markers=", ".join(
                str(b) for b in (archetype.get("behavioral_markers") or [])
            ) or "(none)",
            archetype_counter_segment=archetype.get("counter_segment", "") or "(not specified)",
            archetype_unique=archetype.get("what_makes_them_unique", "") or "(not specified)",
            archetype_stance_tags=", ".join(archetype.get("stance_tags") or []) or "(none)",
            brand_block=brand_block or "(missing)",
            archetype_snippets_block=snippets_block or "(no snippets attributed)",
            hook_candidates_text=hook_candidates_text,
            value_prop_candidates_text=vp_candidates_text,
            ads_for_archetype_block=ads_for_archetype_block or "(no ads aligned with this archetype)",
        )

        print(f"      [CTP-DeepEnrich] '{archetype.get('name', '?')[:50]}' "
              f"with {len(attributed_snippets)} snippets, ~{len(prompt) // 4} tokens")

        try:
            result = await asyncio.wait_for(
                self.llm.complete_json(prompt=prompt, temperature=0.4),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            print(f"      [CTP-DeepEnrich] TIMEOUT after {timeout}s")
            return {}
        except Exception as e:
            print(f"      [CTP-DeepEnrich] FAILED: {type(e).__name__}: {str(e)[:120]}")
            return {}

        if not isinstance(result, dict):
            return {}
        return result

    # Generic stance labels we refuse to emit as a CTP name. When the LLM
    # enrichment fails and we fall back to per-snippet stance_label, those
    # labels often come back as "The Skeptic" / "The Bio-Hacker" — exactly
    # the verbatim repetition we're trying to eliminate. Force a more neutral
    # placeholder so the operator notices the fallback fired.
    _GENERIC_LABELS = {
        "the skeptic", "the fatalist", "the bio-hacker", "the bio_hacker",
        "the desperate seeker", "the passive accepter", "the social conformist",
        "the budget pragmatist", "the authority follower",
        "the optimizer", "the seeker", "the value seeker", "the authority seeker",
        "the community seeker", "the discerning evaluator",
    }

    def _default_enrichment(
        self,
        stance: str,
        snippets: List[Dict[str, Any]],
        stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fallback enrichment when LLM fails."""
        # Use stance_belief from the first snippet's classification, but DO NOT
        # adopt stance_label verbatim — those are the source of cross-brand name
        # repetition. Mark fallback CTPs explicitly so they're easy to spot.
        label = f"Unrefined {stance.replace('_', ' ').title()} (LLM fallback)"
        belief = ""
        product_quote = ""

        for s in snippets:
            sc = s.get("stance_classification", {})
            if sc.get("stance_belief") and not belief:
                belief = sc["stance_belief"]
            if s.get("content") and not product_quote:
                product_quote = s["content"][:200]

        return {
            "ctp_name": label,
            "core_insight_general_stance": belief,
            "core_insight_product_anchored": product_quote,
            "pain_points": [],
            "desires": [],
            "recommended_hooks": [],
            "recommended_value_props": [],
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
            # stance_confidence can be explicitly None (when classifier ran but
            # didn't tag this snippet); fall back to 0.5 in that case too.
            conf = sc.get("stance_confidence")
            score += conf if isinstance(conf, (int, float)) else 0.5
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
        ad_creative_patterns: Optional[Dict[str, Any]] = None,
        brand_context_block: str = "(no brand context available)",
    ) -> Dict[str, Any]:
        """Generate the hypothesis layer for a single CTP.

        Note: ad_library_data and ad_creative_patterns are still accepted for
        backward compat, but they're already aggregated into brand_context_block
        upstream — we don't render them again here.
        """
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
            ctp_name=ctp.ctp_name,
            core_insight=ctp.core_insight_general,
            weight=ctp.weight,
            snippet_count=ctp.snippet_count,
            pain_points_text=pain_points_text,
            barriers_text=barriers_text,
            kill_signals_text=kill_signals_text,
            language_cues_text=", ".join(ctp.top_language_cues[:10]) or "(none)",
            brand_context_block=brand_context_block,
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
    ad_creative_patterns: Any = None,
    brand_context_block: str = "",
    hook_pool: Optional[List[str]] = None,
    value_props_pool: Optional[List[str]] = None,
    corpus: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build CTPs and hypothesis layer.

    Two paths:
      1. DISCOVERY (preferred, when `corpus` is provided): single-shot
         archetype discovery from the full data corpus, then deep
         per-archetype enrichment. Replaces the forced 8-bucket clustering.
      2. STANCE FALLBACK (when corpus is missing or discovery returns
         nothing): the prior cluster-by-stance + enrich path. Kept so
         direct callers (test_ctp_direct.py) and degraded conditions still
         produce output.

    `brand_context_block` is the rendered text from
    services.brand_context.render_context_block(...). It carries everything
    the prompts need to be brand-specific.

    `hook_pool` and `value_props_pool` are the brand's existing pools — the LLM
    selects from them per CTP and supplements with new copy if needed.

    Returns:
        Dict with:
        - ctps:        List of CTP dicts (rich discovery fields when path 1 ran)
        - hypothesis:  List of hypothesis dicts (one per CTP)
        - stats:       Summary statistics with `path` ("discovery"|"stance_fallback")
    """
    builder = CTPBuilder()

    # ── Path 1: DISCOVERY ─────────────────────────────────────────────
    ctps: List[CreativeTargetPersona] = []
    path_used = "stance_fallback"
    if corpus and corpus.get("snippets_block"):
        ctps = await builder.build_ctps_via_discovery(
            brand_name=brand_name,
            corpus=corpus,
            brand_context_block=brand_context_block,
            hook_pool=hook_pool,
            value_props_pool=value_props_pool,
            ad_library_data=ad_library_data,
        )
        if ctps:
            path_used = "discovery"
        else:
            print("    [CTP] Discovery returned 0 archetypes — falling back to stance clustering")

    # ── Path 2: STANCE FALLBACK ───────────────────────────────────────
    if not ctps:
        ctps = await builder.build_ctps(
            classified_snippets,
            brand_name,
            existing_pain_points,
            brand_context_block=brand_context_block,
            hook_pool=hook_pool,
            value_props_pool=value_props_pool,
        )

    if not ctps:
        return {"ctps": [], "hypothesis": [], "stats": {"total_ctps": 0, "total_snippets": 0, "path": path_used}}

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
            ad_creative_patterns=ad_creative_patterns,
            brand_context_block=brand_context_block or "(no brand context available)",
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
            "weight_distribution": {c.ctp_name: c.weight for c in ctps},
            "path": path_used,
            "ctp_sources": [getattr(c, "source", "stance_fallback") for c in ctps],
        }
    }
