"""
Stance Classifier - Tags scraped snippets with General Stance (CTP worldview).
Classifies the psychological worldview a person holds about their problem.
Runs AFTER the Intake Engine (snippet_classifier) so it can use trigger/blocker as context.
"""

import asyncio
from collections import Counter
from typing import Dict, Any, List, Optional
from .llm.client import get_llm_client
from .llm.ctp_prompts import STANCE_CLASSIFICATION_PROMPT


# Hard cap: classifying thousands of tweets is wasteful and causes the CTP
# pipeline to hang. Prioritize high-quality reviews over noisy social posts.
MAX_SNIPPETS_FOR_STANCE = 300

# Source-type quality ranking for stance classification.
# Rebalanced (April 2026): the previous ranking gave reviews scores so dominant
# that 90%+ of the cap was filled by Trustpilot/Reddit. Review-sites attract
# critical voices, which is why "skeptic" appeared in 100% of analyses. The
# rebalanced scores still favor reviews but allow social/UGC enough headroom
# to surface non-skeptical worldviews (enthusiasts, peer-influenced buyers, etc.).
_SOURCE_QUALITY = {
    "trustpilot": 90, "reddit": 90, "g2": 85, "capterra": 85,
    "amazon": 85, "app_store": 80, "google_reviews": 80,
    "site_review": 80, "other_review": 75, "forum": 75,
    "quora": 75, "youtube_comment": 70,
    "tiktok": 70, "instagram": 65, "twitter": 50,
}

# Diversity guarantee for the cap: no single source_type should consume more
# than this fraction of the 300-slot budget. Forces round-robin behavior so
# Trustpilot can't monopolize the cap and silence every other voice.
_PER_SOURCE_CAP_FRACTION = 0.40


def _quality_score(snippet: Dict[str, Any]) -> int:
    """Rank a snippet for stance-classification priority (higher = better)."""
    base = _SOURCE_QUALITY.get(snippet.get("source_type", ""), 50)
    # Longer content carries more signal, up to a 30-pt bonus
    length_bonus = min(30, len(snippet.get("content", "") or "") // 30)
    return base + length_bonus


def _select_with_source_diversity(
    snippets: List[Dict[str, Any]],
    cap: int,
) -> List[Dict[str, Any]]:
    """Select up to `cap` snippets, sorted by quality but with per-source quotas.

    Prevents a single high-quality source (e.g., Trustpilot) from filling the
    entire cap and biasing stance distribution toward review-site psychographics.
    """
    if len(snippets) <= cap:
        return snippets

    per_source_cap = max(1, int(cap * _PER_SOURCE_CAP_FRACTION))

    # Sort by quality desc within each source bucket
    by_source: Dict[str, List[Dict[str, Any]]] = {}
    for s in sorted(snippets, key=_quality_score, reverse=True):
        by_source.setdefault(s.get("source_type", "unknown"), []).append(s)

    # Round-robin: take one from each source until cap is hit
    selected: List[Dict[str, Any]] = []
    consumed: Dict[str, int] = {src: 0 for src in by_source}

    while len(selected) < cap:
        progress = False
        # Iterate sources ordered by their best snippet's quality
        ordered_sources = sorted(
            by_source.keys(),
            key=lambda src: -_quality_score(by_source[src][0]) if by_source[src] else 0,
        )
        for src in ordered_sources:
            if consumed[src] >= per_source_cap:
                continue
            queue = by_source[src]
            if not queue:
                continue
            selected.append(queue.pop(0))
            consumed[src] += 1
            progress = True
            if len(selected) >= cap:
                break
        if not progress:
            # Per-source caps reached; relax the constraint and fill with whatever's left
            for src in ordered_sources:
                while by_source[src] and len(selected) < cap:
                    selected.append(by_source[src].pop(0))
            break

    return selected


# Known stance archetypes for normalization
STANCE_ARCHETYPES = {
    "fatalist", "skeptic", "bio_hacker", "desperate_seeker",
    "passive_accepter", "social_conformist", "budget_pragmatist",
    "authority_follower"
}


class StanceClassifier:
    """Classifies scraped snippets with General Stance for CTP building."""

    def __init__(self):
        self.llm = get_llm_client(task_type="classifier")

    async def classify_batch(
        self,
        snippets: List[Dict[str, Any]],
        batch_size: int = 25,
        concurrency: int = 3,
        brand_context_block: str = "",
    ) -> List[Dict[str, Any]]:
        """
        Classify multiple snippets with general stance using parallel batch LLM calls.

        Args:
            snippets: List of dicts with 'content', 'source_type', etc.
            batch_size: Number of snippets per LLM call (25 = sweet spot for Gemini)
            concurrency: Number of parallel LLM calls
            brand_context_block: Rendered brand-context text from
                services.brand_context.render_context_block(). Without this,
                the prompt will fall back to a "(no brand context available)"
                placeholder and stance interpretations will be generic.

        Returns:
            List of snippets with stance classification added
        """
        self._brand_context_block = brand_context_block or "(no brand context available)"
        if not snippets:
            return []

        # Skip already-classified snippets (cache on reprocess)
        to_classify = []
        already_done = []
        for s in snippets:
            if s.get("general_stance") and s["general_stance"] != "unknown":
                already_done.append(s)
            else:
                to_classify.append(s)

        if already_done:
            print(f"    [Stance] Skipping {len(already_done)} already-classified snippets")

        if not to_classify:
            print(f"    [Stance] All snippets already classified")
            return snippets

        # Cap to top-N highest-quality snippets to prevent runaway classification
        # (prior bug: 1832 Twitter-heavy snippets hung the pipeline for 13+ min).
        # Use round-robin source diversity so Trustpilot can't monopolize the cap.
        if len(to_classify) > MAX_SNIPPETS_FOR_STANCE:
            original_count = len(to_classify)
            to_classify = _select_with_source_diversity(to_classify, MAX_SNIPPETS_FOR_STANCE)
            source_dist = Counter(s.get("source_type", "unknown") for s in to_classify)
            print(
                f"    [Stance] Capped {original_count} -> {len(to_classify)} snippets "
                f"with source diversity (per-source cap = "
                f"{int(MAX_SNIPPETS_FOR_STANCE * _PER_SOURCE_CAP_FRACTION)})"
            )
            print(f"    [Stance] Source distribution: {dict(source_dist)}")

        # Split into batches
        batches = []
        for i in range(0, len(to_classify), batch_size):
            batches.append(to_classify[i:i + batch_size])

        total_batches = len(batches)
        classified_count = 0

        # Process batches in parallel groups
        semaphore = asyncio.Semaphore(concurrency)

        async def process_batch(batch_num: int, batch: List[Dict[str, Any]]) -> int:
            nonlocal classified_count
            async with semaphore:
                print(f"    [Stance] Batch {batch_num + 1}/{total_batches} ({len(batch)} snippets)...", end=" ", flush=True)
                try:
                    batch_prompt = self._build_batch_prompt(batch)
                    response = await asyncio.wait_for(
                        self.llm.complete_json(prompt=batch_prompt, temperature=0.3),
                        timeout=90.0
                    )

                    classifications = None

                    if response and isinstance(response, list):
                        classifications = response
                    elif response and isinstance(response, dict):
                        if "general_stance" in response:
                            print(f"PARTIAL (single object)")
                            self._apply_stance(batch[0], response)
                            classified_count += 1
                            return 1

                        for key in ["classifications", "results", "result", "snippets", "data", "items"]:
                            if key in response and isinstance(response[key], list):
                                classifications = response[key]
                                break

                        if classifications is None:
                            print(f"FAILED (dict keys: {list(response.keys())[:5]})")
                            return 0
                    else:
                        print(f"FAILED (type: {type(response).__name__})")
                        return 0

                    if classifications:
                        count = 0
                        for i, classification in enumerate(classifications):
                            if i < len(batch) and classification and isinstance(classification, dict):
                                self._apply_stance(batch[i], classification)
                                count += 1
                        classified_count += count
                        print(f"OK ({count} classified)")
                        return count

                except asyncio.TimeoutError:
                    print("TIMEOUT")
                except Exception as e:
                    print(f"ERROR: {str(e)[:50]}")
                return 0

        # Run all batches with concurrency limit.
        # return_exceptions=True: one failing batch must not abort the other 36.
        tasks = [process_batch(i, batch) for i, batch in enumerate(batches)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        failures = [r for r in results if isinstance(r, Exception)]
        if failures:
            print(
                f"    [Stance] {len(failures)}/{len(tasks)} batches raised exceptions; "
                f"continuing with partial data. First error: {type(failures[0]).__name__}: {str(failures[0])[:80]}"
            )

        print(f"    [Stance] Total: {classified_count}/{len(to_classify)} snippets classified")
        return snippets  # Return all (including already_done)

    # Fuzzy keyword -> canonical stance mapping. Used when the LLM invents
    # descriptive stance keys like "satisfied_user" or "community_observer"
    # instead of picking from the fixed taxonomy. Prevents runaway CTP clustering
    # (a prior session generated 48 stances from 300 snippets → 48 CTP LLM calls).
    _STANCE_NORMALIZATION_KEYWORDS = [
        ("fatalist",          ["fatal", "gave_up", "inevitable", "genetic", "permanent", "hopeless"]),
        ("skeptic",           ["skeptic", "sceptic", "critic", "doubt", "burned", "proof_seeker", "discerning", "evaluator"]),
        ("bio_hacker",        ["bio_hacker", "biohacker", "optimizer", "stacker", "experimenter", "researcher"]),
        ("desperate_seeker",  ["desperate", "urgent", "crisis", "seeker", "acute"]),
        ("passive_accepter",  ["passive", "accepter", "resigned", "indifferent", "observer"]),
        ("social_conformist", ["social", "conformist", "community", "peer", "participant"]),
        ("budget_pragmatist", ["budget", "pragmat", "value", "price", "cost_conscious", "frugal"]),
        ("authority_follower",["authority", "follower", "expert", "doctor", "professional", "official"]),
    ]

    @classmethod
    def _normalize_stance(cls, stance_raw: str) -> str:
        """Collapse any LLM-invented stance into one of the 8 canonical archetypes."""
        if not stance_raw:
            return "unknown"
        s = stance_raw.lower().strip().replace(" ", "_").replace("-", "_")
        if s in STANCE_ARCHETYPES:
            return s
        # Keyword-based fuzzy match
        for canonical, keywords in cls._STANCE_NORMALIZATION_KEYWORDS:
            if any(kw in s for kw in keywords):
                return canonical
        # Fallback: unknown (will be dropped by the CTP builder)
        return "unknown"

    def _apply_stance(self, snippet: Dict[str, Any], classification: Dict[str, Any]):
        """Apply stance classification to a snippet dict."""
        raw = classification.get("general_stance", "unknown")
        stance = self._normalize_stance(raw)

        snippet["general_stance"] = stance
        snippet["stance_label"] = classification.get("stance_label", stance.replace("_", " ").title())
        snippet["stance_belief"] = classification.get("stance_belief", "")
        snippet["stance_confidence"] = classification.get("stance_confidence", 0.5)
        snippet["stance_classification"] = classification

    async def _classify_single(self, snippet: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Fallback: classify a single snippet individually."""
        content = (snippet.get("content") or "")[:500]
        if len(content.strip()) < 20:
            return None

        prompt = self._build_batch_prompt([snippet])
        try:
            result = await asyncio.wait_for(
                self.llm.complete_json(prompt=prompt, temperature=0.3),
                timeout=30.0
            )
            if isinstance(result, list) and result:
                return result[0]
            if isinstance(result, dict) and "general_stance" in result:
                return result
        except Exception:
            pass
        return None

    def _build_batch_prompt(self, snippets: List[Dict[str, Any]]) -> str:
        """Build prompt for batch stance classification."""
        snippets_text = ""
        for i, s in enumerate(snippets):
            content = (s.get("content") or "")[:400]
            source = s.get("source_type", "unknown")
            trigger = s.get("primary_trigger", "")
            blocker = s.get("blocker_type", "")
            outcome = s.get("desired_outcome_level", "")
            proof = s.get("proof_type_trusted", "")

            context_parts = []
            if trigger:
                context_parts.append(f"trigger={trigger}")
            if blocker:
                context_parts.append(f"blocker={blocker}")
            if outcome:
                context_parts.append(f"outcome={outcome}")
            if proof:
                context_parts.append(f"proof={proof}")
            context_str = ", ".join(context_parts) if context_parts else "no intake tags"

            snippets_text += f"""
SNIPPET #{i + 1}:
Content: "{content}"
Source: {source}
Intake Tags: [{context_str}]
---"""

        return STANCE_CLASSIFICATION_PROMPT.format(
            num_snippets=len(snippets),
            snippets_text=snippets_text,
            brand_context_block=getattr(self, "_brand_context_block", "(no brand context available)"),
        )
