"""
Snippet Classifier - Tags scraped snippets with Intake Engine dimensions.
Classifies: Primary Trigger, Blocker Type, Desired Outcome Level, Proof Type.
"""

import asyncio
from typing import Dict, Any, List, Optional
from .llm.client import get_llm_client


CLASSIFICATION_PROMPT = """You are an expert customer research analyst. Classify this snippet from customer feedback/reviews.

SNIPPET:
"{content}"

SOURCE: {source_type}
CONTEXT: {context}

CLASSIFY with these dimensions:

1. PRIMARY_TRIGGER: Why is the customer searching/talking about this now?
   Examples: "health_scare", "life_change", "product_failure", "recommendation", "curiosity", "price_shopping", "problem_worsening", "seasonal_need"

2. BLOCKER_TYPE: What's stopping them?
   - "friction" = CAN'T (lack of knowledge, access, time, money)
   - "objection" = WON'T (skeptical, doesn't trust, disagrees with approach)
   - "none" = No blocker mentioned

3. DESIRED_OUTCOME_LEVEL: What level of outcome do they want?
   - "functional" = practical, measurable result (works, saves time, cheaper)
   - "emotional" = feeling-based (peace of mind, confidence, relief)
   - "identity" = who they want to be (good parent, healthy person, smart consumer)

4. PROOF_TYPE_TRUSTED: What evidence would convince them? (pick most relevant)
   - "vet_science" = veterinary/scientific/medical backing
   - "reviews_ugc" = other customer reviews and experiences
   - "transparency" = knowing ingredients/sources/processes
   - "price_math" = cost comparison, value calculation
   - "certifications" = official certifications, awards
   - "before_after" = visible transformation/results
   - "expert_endorsement" = professional recommendations
   - "none" = no proof type evident

5. LANGUAGE_CUES: Extract 2-4 notable phrases, emotional words, or slang used.

6. LANGUAGE: Detect language code (en, es, pt, fr, de, etc.)

Return JSON only:
{{
    "primary_trigger": "trigger_label",
    "blocker_type": "friction|objection|none",
    "desired_outcome_level": "functional|emotional|identity",
    "proof_type_trusted": "proof_type",
    "language_cues": ["phrase1", "phrase2"],
    "language": "en",
    "confidence": 0.85
}}

If unclear, use your best judgment and lower confidence score."""


class SnippetClassifier:
    """Classifies scraped snippets with Intake Engine dimensions."""
    
    def __init__(self):
        # Use Gemini specifically because it properly returns JSON arrays for batch prompts
        # OpenAI tends to return single objects even when asked for arrays
        self.llm = get_llm_client(provider="gemini")
    
    async def classify_snippet(
        self, 
        content: str, 
        source_type: str,
        context: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        Classify a single snippet.
        
        Args:
            content: The snippet text
            source_type: Where it came from (reddit, trustpilot, etc.)
            context: Additional context (title, product name, etc.)
            
        Returns:
            Classification dict or None
        """
        if not content or len(content.strip()) < 20:
            return None
        
        prompt = CLASSIFICATION_PROMPT.format(
            content=content[:1000],  # Limit length
            source_type=source_type,
            context=context[:200] if context else "N/A"
        )
        
        try:
            result = await asyncio.wait_for(
                self.llm.complete_json(prompt=prompt, temperature=0.3),
                timeout=30.0  # 30s per classification
            )
            if result and isinstance(result, dict):
                # Validate fields
                return {
                    "primary_trigger": result.get("primary_trigger", "unknown"),
                    "blocker_type": result.get("blocker_type", "none"),
                    "desired_outcome_level": result.get("desired_outcome_level", "functional"),
                    "proof_type_trusted": result.get("proof_type_trusted", "none"),
                    "language_cues": result.get("language_cues", []),
                    "language": result.get("language", "en"),
                    "confidence": result.get("confidence", 0.5)
                }
        except asyncio.TimeoutError:
            # Silent timeout, will count as failed
            pass
        except Exception as e:
            # Log first few errors only
            print(f"    [!] Classification error: {type(e).__name__}: {str(e)[:50]}")
        
        return None
    
    async def classify_batch(
        self,
        snippets: List[Dict[str, Any]],
        batch_size: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Classify multiple snippets using BATCH LLM calls.
        Sends multiple snippets in a single prompt for efficiency.
        
        Args:
            snippets: List of dicts with 'content', 'source_type', 'context'
            batch_size: Number of snippets per LLM call
            
        Returns:
            List of snippets with classification added
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
            
            print(f"    [Classifier] Batch {batch_num + 1}/{total_batches} ({len(batch)} snippets)...", end=" ", flush=True)
            
            try:
                # Build batch prompt
                batch_prompt = self._build_batch_prompt(batch)
                
                # Single LLM call for all snippets in batch
                response = await asyncio.wait_for(
                    self.llm.complete_json(prompt=batch_prompt, temperature=0.3),
                    timeout=60.0  # Longer timeout for batch
                )
                
                # Parse batch response - handle multiple formats
                classifications = None
                
                if response and isinstance(response, list):
                    # Direct array response (ideal)
                    classifications = response
                elif response and isinstance(response, dict):
                    # Check if this is a SINGLE classification (not wrapped)
                    # This happens when LLM returns one object instead of array
                    if "primary_trigger" in response or "blocker_type" in response:
                        # LLM returned a single classification object - apply to first and retry rest individually
                        print(f"PARTIAL (got single object, will retry rest individually)")
                        batch[0].update(response)
                        batch[0]["classification"] = response
                        classified_count += 1
                        
                        # Retry remaining snippets individually
                        for j, item in enumerate(batch[1:], 1):
                            try:
                                individual_result = await asyncio.wait_for(
                                    self.classify_snippet(
                                        content=item.get("content", ""),
                                        source_type=item.get("source_type", "unknown"),
                                        context=item.get("context", "")
                                    ),
                                    timeout=30.0
                                )
                                if individual_result:
                                    item.update(individual_result)
                                    item["classification"] = individual_result
                                    classified_count += 1
                                else:
                                    item["classification_error"] = "individual_failed"
                            except Exception as retry_err:
                                item["classification_error"] = f"retry_failed: {str(retry_err)[:30]}"
                        
                        results.extend(batch)
                        continue
                    
                    # Wrapped response - try multiple keys
                    for key in ["classifications", "results", "result", "snippets", "data", "items"]:
                        if key in response and isinstance(response[key], list):
                            classifications = response[key]
                            break
                    
                    # If still no list found, log the response structure
                    if classifications is None:
                        print(f"FAILED (dict with keys: {list(response.keys())[:5]})")
                        for item in batch:
                            item["classification_error"] = f"unexpected_keys: {list(response.keys())[:3]}"
                        results.extend(batch)
                        continue
                else:
                    print(f"FAILED (unexpected response type: {type(response).__name__})")
                    for item in batch:
                        item["classification_error"] = f"type_{type(response).__name__}"
                    results.extend(batch)
                    continue
                
                # Process the classifications
                if classifications:
                    for i, classification in enumerate(classifications):
                        if i < len(batch):
                            if classification and isinstance(classification, dict):
                                batch[i].update(classification)
                                batch[i]["classification"] = classification
                                classified_count += 1
                            else:
                                batch[i]["classification_error"] = "invalid_item"
                    print(f"OK ({len([c for c in classifications if c])} classified)")
                
                results.extend(batch)
                
                # Small delay between batches to avoid rate limits
                await asyncio.sleep(0.3)
                
            except asyncio.TimeoutError:
                print("TIMEOUT")
                for item in batch:
                    item["classification_error"] = "timeout"
                results.extend(batch)
            except Exception as e:
                print(f"ERROR: {str(e)[:50]}")
                for item in batch:
                    item["classification_error"] = str(e)[:50]
                results.extend(batch)
        
        print(f"    [Classifier] Total: {classified_count}/{len(snippets)} snippets classified")
        return results
    
    def _build_batch_prompt(self, snippets: List[Dict[str, Any]]) -> str:
        """Build a prompt to classify multiple snippets at once."""
        snippets_text = ""
        for i, s in enumerate(snippets):
            content = (s.get("content") or "")[:400]  # Shorter for batch
            source = s.get("source_type", "unknown")
            context = (s.get("context") or s.get("title") or "")[:100]
            snippets_text += f"""
SNIPPET #{i + 1}:
Content: "{content}"
Source: {source}
Context: {context}
---"""
        
        return f"""You are classifying customer feedback snippets. There are {len(snippets)} snippets below.

{snippets_text}

Classify EACH of the {len(snippets)} snippets above with these dimensions:
- primary_trigger: Why is the customer searching? (health_scare, life_change, product_failure, recommendation, curiosity, price_shopping, problem_worsening, seasonal_need)
- blocker_type: What stops them? (friction, objection, none)
- desired_outcome_level: What outcome? (functional, emotional, identity)
- proof_type_trusted: What evidence convinces them? (vet_science, reviews_ugc, transparency, price_math, certifications, before_after, expert_endorsement, none)
- language_cues: 2-3 notable phrases from the text
- language: Language code (en, es, etc.)
- confidence: 0.0-1.0

You MUST return a JSON array with EXACTLY {len(snippets)} objects. Each object corresponds to one snippet in order.

Example response format:
[
  {{"primary_trigger": "recommendation", "blocker_type": "none", "desired_outcome_level": "functional", "proof_type_trusted": "reviews_ugc", "language_cues": ["phrase1"], "language": "en", "confidence": 0.9}},
  {{"primary_trigger": "price_shopping", "blocker_type": "objection", "desired_outcome_level": "functional", "proof_type_trusted": "price_math", "language_cues": ["phrase2"], "language": "en", "confidence": 0.8}}
]

Return ONLY the JSON array, no other text."""
    
    def detect_language(self, text: str) -> str:
        """Simple language detection based on common words."""
        text_lower = text.lower()
        
        # Spanish indicators
        spanish_words = ["que", "es", "el", "la", "de", "en", "un", "una", "por", "para", "con", "muy", "pero", "como"]
        spanish_count = sum(1 for w in spanish_words if f" {w} " in f" {text_lower} ")
        
        # English indicators
        english_words = ["the", "is", "are", "was", "were", "have", "has", "been", "this", "that", "with", "for", "but"]
        english_count = sum(1 for w in english_words if f" {w} " in f" {text_lower} ")
        
        if spanish_count > english_count and spanish_count >= 3:
            return "es"
        return "en"


async def classify_session_snippets(session_id: int, db_session) -> int:
    """
    Classify all unclassified snippets for a session.
    
    Args:
        session_id: Research session ID
        db_session: Database session
        
    Returns:
        Number of snippets classified
    """
    from sqlalchemy import select
    from ..models import ScrapedData
    
    classifier = SnippetClassifier()
    
    # Get unclassified snippets
    result = await db_session.execute(
        select(ScrapedData)
        .where(ScrapedData.session_id == session_id)
        .where(ScrapedData.primary_trigger.is_(None))
        .where(ScrapedData.content.isnot(None))
        .limit(100)  # Batch limit
    )
    snippets = result.scalars().all()
    
    if not snippets:
        print(f"    [Classifier] No unclassified snippets found for session {session_id}")
        return 0
    
    print(f"    [Classifier] Found {len(snippets)} unclassified snippets")
    
    # Prepare for classification
    snippet_dicts = [
        {
            "id": s.id,
            "content": s.content,
            "source_type": s.source_type,
            "title": s.title or ""
        }
        for s in snippets
    ]
    
    # Classify
    classified = await classifier.classify_batch(snippet_dicts)
    
    # Update database
    updated = 0
    for classified_dict in classified:
        if classified_dict.get("primary_trigger"):
            snippet_id = classified_dict["id"]
            # Find and update the snippet
            for s in snippets:
                if s.id == snippet_id:
                    s.primary_trigger = classified_dict.get("primary_trigger")
                    s.blocker_type = classified_dict.get("blocker_type")
                    s.desired_outcome_level = classified_dict.get("desired_outcome_level")
                    s.proof_type_trusted = classified_dict.get("proof_type_trusted")
                    s.language_cues = classified_dict.get("language_cues")
                    s.language = classified_dict.get("language")
                    s.classification_confidence = classified_dict.get("confidence")
                    updated += 1
                    break
    
    await db_session.commit()
    print(f"    [Classifier] Updated {updated} snippets in database")
    
    return updated
