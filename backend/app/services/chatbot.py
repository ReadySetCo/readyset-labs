# -*- coding: utf-8 -*-
"""
AI Chatbot Service v4 - Full Context approach.
Loads ALL session data directly into the LLM context instead of RAG chunks.
With 1M token context (Gemini), all scraped data fits easily (~50-80K tokens).
Falls back to RAG semantic search only for extremely large sessions.
"""

import json
import asyncio
import logging
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from .research_api import ResearchAPI, ResearchPack
from .llm.client import get_llm_client
from ..models import ScrapedData, Insight, Brand, ResearchSession

# Setup logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout, force=True)
logger = logging.getLogger(__name__)

# Max chars before falling back to RAG (roughly 300K tokens)
FULL_CONTEXT_CHAR_LIMIT = 900_000

SYSTEM_PROMPT = """You are a brand research analyst. You help marketing teams extract actionable insights from real customer data.

You have access to the COMPLETE research dataset including:
- Every piece of scraped content from Reddit, Twitter, TikTok, Instagram, forums, reviews, news, etc.
- Brand information (name, sector, description, social URLs)
- Analyzed insights: pain points, ICPs, messaging angles, objections, hooks
- Ad Library analysis: ad transcriptions, creative patterns, frameworks
- Competitor intelligence and SWOT analysis
- TikTok trends, Instagram brand presence data

RULES:
1. Base ALL answers on the provided data. NEVER invent quotes, stats, or facts.
2. When citing customer feedback, use EXACT quotes from the data with the source: "[reddit] exact quote here"
3. If something isn't in the data, say so clearly.
4. Be specific — name sources, platforms, authors when available.
5. When asked for quotes or verbatims, pull the ACTUAL text from the scraped data section.
6. For ad analysis questions, reference specific ad transcriptions and patterns.
7. Be concise and actionable. Marketing teams need clear, usable insights.
8. You can answer in the user's language (if they write in Spanish, answer in Spanish).
"""


class ChatbotService:
    """AI Chatbot with full-context data loading."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.api = ResearchAPI(db)
        # Use dedicated chat model (large context, stable)
        from ..config import settings
        self.llm = get_llm_client(provider="gemini")
        # Override model for chat to use the chat-specific model
        if hasattr(settings, 'GEMINI_CHAT_MODEL') and settings.GEMINI_CHAT_MODEL:
            import google.generativeai as genai
            self.llm.gemini_model = genai.GenerativeModel(settings.GEMINI_CHAT_MODEL)
            self.llm.model = settings.GEMINI_CHAT_MODEL
            logger.info(f"[Chat] Using chat model: {settings.GEMINI_CHAT_MODEL}")
        self.conversation_history: List[Dict[str, str]] = []
        self.current_pack: Optional[ResearchPack] = None
        self._context_cache: Dict[int, str] = {}  # session_id -> context string

    async def chat(
        self,
        message: str,
        session_id: Optional[int] = None,
        brand_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Process chat message with full context loading."""
        logger.info(f"[Chat] Message for session_id={session_id}: '{message[:60]}...'")

        if not session_id:
            return self._response("Please open a research session to use the chat. I need data to work with.")

        # === LOAD RESEARCH PACK (for status check) ===
        try:
            pack = await self.api.get_research_pack(session_id)
            self.current_pack = pack
        except Exception as e:
            logger.error(f"[Chat] Error getting pack: {e}")
            return self._response(f"Error loading research data: {str(e)}")

        if pack.status == "not_found":
            return self._response(f"Session {session_id} not found.")

        if pack.status == "running":
            return self._response(
                f"Research is still running ({pack.stats.get('total_items', 0)} items collected so far). "
                f"Try again when it completes."
            )

        # === BUILD FULL CONTEXT ===
        try:
            context = await self._build_full_context(session_id, pack)
            context_source = "full_data"
            logger.info(f"[Chat] Context built: {len(context):,} chars ({context_source})")
        except Exception as e:
            logger.error(f"[Chat] Context build error: {e}")
            # Fallback to pack-only context
            context = pack.to_context_string()
            context_source = "pack_only"

        # === BUILD PROMPT WITH CONVERSATION HISTORY ===
        history_text = ""
        if self.conversation_history:
            recent = self.conversation_history[-10:]  # Last 5 exchanges
            history_parts = []
            for msg in recent:
                role = "User" if msg["role"] == "user" else "Assistant"
                history_parts.append(f"**{role}**: {msg['content'][:500]}")
            history_text = "\n\n## Previous conversation:\n" + "\n".join(history_parts)

        prompt = f"""## Complete Research Data:
{context}
{history_text}

## Current Question:
{message}

Answer based ONLY on the research data above. Cite sources with exact quotes when relevant. Format: [source_type] "exact quote" """

        logger.info(f"[Chat] Total prompt: {len(prompt):,} chars, history: {len(self.conversation_history)} msgs")

        # === CALL LLM ===
        try:
            response = await asyncio.wait_for(
                self.llm.complete(
                    prompt=prompt,
                    system_prompt=SYSTEM_PROMPT,
                    temperature=0.4,  # Lower temp for more factual responses
                    max_tokens=8000,  # More room for detailed answers with citations
                ),
                timeout=120.0  # 2 min timeout for large contexts
            )

            if not response:
                return self._response("I couldn't generate a response. Please try rephrasing.")

            # Update conversation history
            self.conversation_history.append({"role": "user", "content": message})
            self.conversation_history.append({"role": "assistant", "content": response})

            return self._response(response, context_source=context_source)

        except asyncio.TimeoutError:
            logger.warning("[Chat] LLM timeout (120s)")
            return self._response("Request timed out. The model is processing a lot of data — please try again.")
        except Exception as e:
            logger.error(f"[Chat] LLM error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return self._response(f"Error: {type(e).__name__}. Please try again.")

    async def _build_full_context(self, session_id: int, pack: ResearchPack) -> str:
        """
        Build complete context with ALL session data.
        Loads everything from DB and formats for the LLM.
        """
        # Check cache first
        if session_id in self._context_cache:
            logger.info(f"[Chat] Using cached context for session {session_id}")
            return self._context_cache[session_id]

        parts = []

        # === 1. BRAND INFO ===
        brand_info = pack.brand_info
        parts.append("# Brand Information")
        parts.append(f"**Name**: {brand_info.get('name', 'Unknown')}")
        parts.append(f"**Sector**: {brand_info.get('sector', 'N/A')}")
        parts.append(f"**Website**: {brand_info.get('website', 'N/A')}")
        if brand_info.get('description'):
            parts.append(f"**Description**: {brand_info['description']}")

        # === 2. ALL SCRAPED DATA (the raw customer feedback) ===
        parts.append("\n\n# Scraped Customer Data (ALL sources)")
        parts.append("This is the complete dataset of customer feedback, reviews, posts, and discussions.\n")

        result = await self.db.execute(
            select(ScrapedData)
            .where(ScrapedData.session_id == session_id)
            .where(ScrapedData.content.isnot(None))
            .order_by(ScrapedData.source_type, ScrapedData.likes.desc().nullslast())
        )
        all_data = result.scalars().all()

        # Group by source type for readability
        by_source: Dict[str, List] = {}
        for item in all_data:
            content = (item.content or "").strip()
            if len(content) < 15:
                continue
            source = item.source_type or "unknown"
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(item)

        total_content_chars = 0
        for source_type, items in sorted(by_source.items()):
            parts.append(f"\n## {source_type.upper()} ({len(items)} items)")
            for item in items:
                content = (item.content or "").strip()
                sentiment = f" | sentiment: {item.sentiment}" if item.sentiment else ""
                author = f" | by: @{item.author}" if item.author else ""
                url = f" | url: {item.source_url}" if item.source_url else ""
                likes = f" | likes: {item.likes}" if item.likes else ""

                entry = f"- [{source_type}{sentiment}{author}{likes}{url}]: \"{content}\""
                parts.append(entry)
                total_content_chars += len(entry)

                # Add video analysis if present
                if item.video_analysis:
                    va = item.video_analysis if isinstance(item.video_analysis, dict) else {}
                    if isinstance(item.video_analysis, str):
                        try:
                            va = json.loads(item.video_analysis)
                        except:
                            va = {}
                    if va:
                        transcript = va.get("transcription", va.get("transcript", ""))
                        if transcript:
                            parts.append(f"  Video transcript: \"{transcript[:500]}\"")
                        hook = va.get("hook", va.get("hook_text", ""))
                        if hook:
                            parts.append(f"  Video hook: \"{hook}\"")

        logger.info(f"[Chat] Scraped data: {len(all_data)} items, {total_content_chars:,} chars")

        # === 3. INSIGHTS (analyzed data) ===
        result = await self.db.execute(
            select(Insight).where(Insight.session_id == session_id)
        )
        insights = result.scalars().all()

        if insights:
            insight = insights[-1]  # Most recent
            parts.append("\n\n# Analyzed Insights")

            # Core insights
            self._add_json_section(parts, "Brand Summary", insight.brand_summary)
            self._add_json_section(parts, "Pain Points", insight.pain_points)
            self._add_json_section(parts, "Value Propositions", insight.value_props)
            self._add_json_section(parts, "ICPs (Ideal Customer Profiles)", insight.icps)
            self._add_json_section(parts, "Messaging Angles", insight.messaging_angles)
            self._add_json_section(parts, "Objections", insight.objections)
            self._add_json_section(parts, "Verbatim Quotes", insight.verbatim_quotes)
            self._add_json_section(parts, "Customer Language", insight.customer_language)
            self._add_json_section(parts, "Customer Desires", insight.customer_desires)
            self._add_json_section(parts, "Purchase Triggers", insight.purchase_triggers)
            self._add_json_section(parts, "Recommended Hooks", insight.recommended_hooks)

            # Cross-source insights
            self._add_json_section(parts, "Cross-Source Insights", insight.cross_source_insights)

            # Competitive intelligence
            self._add_json_section(parts, "Competitor Profiles", insight.competitor_profiles)
            self._add_json_section(parts, "Competitive Matrix", insight.competitive_matrix)
            self._add_json_section(parts, "SWOT Analysis", insight.swot_analysis)

            # Platform-specific
            self._add_json_section(parts, "TikTok Trends", insight.tiktok_trends)
            self._add_json_section(parts, "Instagram Brand Presence", insight.instagram_brand_presence)
            self._add_json_section(parts, "Hooks Library", insight.hooks_library)

            # Ad Library
            self._add_json_section(parts, "Ad Creative Patterns", insight.ad_creative_patterns)
            self._add_json_section(parts, "Ad Library Data (Brand Ads)", insight.ad_library_data)
            self._add_json_section(parts, "Competitor Ads Data", insight.competitor_ads_data)

            # Generated content
            self._add_json_section(parts, "Generated Scripts", insight.generated_scripts)
            self._add_json_section(parts, "Full Report", insight.full_report)

        # === 4. STATS ===
        parts.append(f"\n\n# Data Statistics")
        stats = pack.stats
        parts.append(f"Total items: {stats.get('total_items', 0)}")
        parts.append(f"Sources: {', '.join(stats.get('sources', []))}")
        if stats.get('sentiment_avg') is not None:
            parts.append(f"Average sentiment score: {stats['sentiment_avg']:.3f}")

        context = "\n".join(parts)

        # Check if context is too large — fall back to summarized version
        if len(context) > FULL_CONTEXT_CHAR_LIMIT:
            logger.warning(f"[Chat] Context too large ({len(context):,} chars), trimming ad data...")
            # Rebuild without the heaviest fields (competitor_ads_data, ad_library_data raw)
            context = self._trim_context(context)

        # Cache it
        self._context_cache[session_id] = context
        logger.info(f"[Chat] Final context: {len(context):,} chars (~{int(len(context)*0.3):,} tokens)")

        return context

    def _add_json_section(self, parts: List[str], title: str, data) -> None:
        """Add a JSON field as a readable section."""
        if not data:
            return

        if isinstance(data, str):
            if len(data.strip()) < 5:
                return
            # Try to parse as JSON for better formatting
            try:
                parsed = json.loads(data)
                parts.append(f"\n## {title}")
                parts.append(json.dumps(parsed, indent=2, ensure_ascii=False, default=str))
                return
            except (json.JSONDecodeError, TypeError):
                parts.append(f"\n## {title}")
                parts.append(data)
                return

        if isinstance(data, (dict, list)):
            if not data:
                return
            parts.append(f"\n## {title}")
            parts.append(json.dumps(data, indent=2, ensure_ascii=False, default=str))

    def _trim_context(self, context: str) -> str:
        """Trim context if it exceeds the limit by removing the heaviest sections."""
        # Simple approach: truncate from the end of the insights section
        if len(context) > FULL_CONTEXT_CHAR_LIMIT:
            return context[:FULL_CONTEXT_CHAR_LIMIT] + "\n\n[... context trimmed for size ...]"
        return context

    def _response(self, text: str, context_source: str = "none") -> Dict[str, Any]:
        """Create standard response object."""
        return {
            "response": text,
            "sources": [],
            "timestamp": datetime.now().isoformat(),
            "pack_status": self.current_pack.status if self.current_pack else "unknown",
            "context_source": context_source,
        }

    async def generate_script(
        self,
        session_id: int,
        prompt: str = "",
        style: str = "ugc"
    ) -> Dict[str, Any]:
        """Generate ad script using research data."""
        pack = await self.api.get_research_pack(session_id)

        if pack.status not in ("ready", "partial"):
            return {"error": f"Research not ready: {pack.status}"}

        script_prompt = f"""Generate a {style}-style ad script for:

Brand: {pack.brand_info.get('name', 'Unknown')}
Sector: {pack.brand_info.get('sector', 'Unknown')}

Pain Points to address: {', '.join(pack.insights_summary.get('pain_points', ['general problems'])[:3])}
Value Props to highlight: {', '.join(pack.insights_summary.get('value_props', ['product benefits'])[:3])}

{prompt or 'Create a compelling 30-second ad script.'}

Format:
1. HOOK (0-3s): Attention grabber
2. PROBLEM (3-10s): Relatable pain
3. SOLUTION (10-20s): Product intro + benefit
4. PROOF (20-25s): Social proof / testimonial
5. CTA (25-30s): Clear call to action

Include visual directions for each scene."""

        try:
            response = await asyncio.wait_for(
                self.llm.complete(prompt=script_prompt, temperature=0.8),
                timeout=60.0
            )
            return {
                "script": response,
                "style": style,
                "session_id": session_id,
                "brand": pack.brand_info.get("name"),
            }
        except Exception as e:
            return {"error": str(e)}

    async def find_verbatims(
        self,
        session_id: int,
        topic: str = "",
        sentiment: str = "any",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Find customer quotes."""
        filters = {}
        if sentiment != "any":
            filters["sentiment"] = sentiment

        results = await self.api.search_text(
            session_id,
            query=topic,
            filters=filters,
            limit=limit
        )

        return [
            {
                "quote": r.get("content", "")[:300],
                "source": r.get("source_type", "unknown"),
                "sentiment": r.get("sentiment"),
                "author": r.get("author"),
                "url": r.get("source_url"),
            }
            for r in results
            if not r.get("error")
        ]

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
        self.current_pack = None
        self._context_cache = {}
