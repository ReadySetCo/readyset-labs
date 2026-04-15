"""
Stance Classifier - Tags scraped snippets with General Stance (CTP worldview).
Classifies the psychological worldview a person holds about their problem.
Runs AFTER the Intake Engine (snippet_classifier) so it can use trigger/blocker as context.
"""

import asyncio
from typing import Dict, Any, List, Optional
from .llm.client import get_llm_client
from .llm.ctp_prompts import STANCE_CLASSIFICATION_PROMPT


# Known stance archetypes for normalization
STANCE_ARCHETYPES = {
    "fatalist", "skeptic", "bio_hacker", "desperate_seeker",
    "passive_accepter", "social_conformist", "budget_pragmatist",
    "authority_follower"
}


class StanceClassifier:
    """Classifies scraped snippets with General Stance for CTP building."""

    def __init__(self):
        self.llm = get_llm_client(provider="gemini")

    async def classify_batch(
        self,
        snippets: List[Dict[str, Any]],
        batch_size: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Classify multiple snippets with general stance using batch LLM calls.

        Args:
            snippets: List of dicts with 'content', 'source_type', and optionally
                      'primary_trigger', 'blocker_type', 'desired_outcome_level', etc.
            batch_size: Number of snippets per LLM call

        Returns:
            List of snippets with stance classification added
        """
        if not snippets:
            return []

        results = []
        total_batches = (len(snippets) + batch_size - 1) // batch_size
        classified_count = 0

        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(snippets))
            batch = snippets[start_idx:end_idx]

            print(f"    [Stance] Batch {batch_num + 1}/{total_batches} ({len(batch)} snippets)...", end=" ", flush=True)

            try:
                batch_prompt = self._build_batch_prompt(batch)

                response = await asyncio.wait_for(
                    self.llm.complete_json(prompt=batch_prompt, temperature=0.3),
                    timeout=60.0
                )

                classifications = None

                if response and isinstance(response, list):
                    classifications = response
                elif response and isinstance(response, dict):
                    if "general_stance" in response:
                        # Single object returned — apply to first, retry rest
                        print(f"PARTIAL (single object)")
                        self._apply_stance(batch[0], response)
                        classified_count += 1

                        for item in batch[1:]:
                            individual = await self._classify_single(item)
                            if individual:
                                self._apply_stance(item, individual)
                                classified_count += 1

                        results.extend(batch)
                        continue

                    for key in ["classifications", "results", "result", "snippets", "data", "items"]:
                        if key in response and isinstance(response[key], list):
                            classifications = response[key]
                            break

                    if classifications is None:
                        print(f"FAILED (dict keys: {list(response.keys())[:5]})")
                        results.extend(batch)
                        continue
                else:
                    print(f"FAILED (type: {type(response).__name__})")
                    results.extend(batch)
                    continue

                if classifications:
                    for i, classification in enumerate(classifications):
                        if i < len(batch) and classification and isinstance(classification, dict):
                            self._apply_stance(batch[i], classification)
                            classified_count += 1
                    print(f"OK ({len([c for c in classifications if c])} classified)")

                results.extend(batch)
                await asyncio.sleep(0.3)

            except asyncio.TimeoutError:
                print("TIMEOUT")
                results.extend(batch)
            except Exception as e:
                print(f"ERROR: {str(e)[:50]}")
                results.extend(batch)

        print(f"    [Stance] Total: {classified_count}/{len(snippets)} snippets classified")
        return results

    def _apply_stance(self, snippet: Dict[str, Any], classification: Dict[str, Any]):
        """Apply stance classification to a snippet dict."""
        stance = classification.get("general_stance", "unknown")
        # Normalize to known archetype if close match
        stance_lower = stance.lower().replace(" ", "_").replace("-", "_")
        if stance_lower in STANCE_ARCHETYPES:
            stance = stance_lower

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
            snippets_text=snippets_text
        )
