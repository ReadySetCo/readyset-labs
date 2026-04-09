# -*- coding: utf-8 -*-
"""
Knowledge Synthesizer - Orchestrates content processing for RAG.

Processes all scraped data using specialized processors per source type,
generates structured knowledge documents for AnythingLLM.
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

import google.generativeai as genai

from ..models import ResearchSession, ScrapedData, Brand, Insight
from .processors import (
    get_processor_for_source,
    ReviewProcessor,
    SocialProcessor,
    DiscussionProcessor,
    VideoProcessor,
    ArticleProcessor,
    CompetitiveProcessor,
    BrandProcessor,
    AdLibraryProcessor,
)

logger = logging.getLogger(__name__)


class KnowledgeSynthesizer:
    """
    Orchestrates content processing for RAG knowledge base.
    
    Uses Gemini to process scraped data into structured format,
    then generates documents optimized for AnythingLLM.
    """
    
    def __init__(
        self,
        output_dir: str = "knowledge_base_processed",
        use_llm: bool = True,
        batch_size: int = 10
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.use_llm = use_llm
        self.batch_size = batch_size
        self.llm_client = None
        
        if use_llm:
            self._init_gemini()
    
    def _init_gemini(self):
        """Initialize Gemini client."""
        from ..config import settings
        api_key = settings.GEMINI_API_KEY
        if api_key:
            genai.configure(api_key=api_key)
            # Using Gemini 2.5 Flash - latest stable model
            self.llm_client = genai.GenerativeModel('gemini-3-flash-preview')
            logger.info("[KnowledgeSynthesizer] Gemini 2.5 Flash initialized")
            print("[KnowledgeSynthesizer] Gemini 2.5 Flash initialized - LLM mode active")
        else:
            logger.warning("[KnowledgeSynthesizer] No GEMINI_API_KEY in settings, running without LLM")
            print("[KnowledgeSynthesizer] WARNING: No GEMINI_API_KEY, running in BASIC mode (no LLM)")
            self.use_llm = False
    
    async def synthesize_session(
        self,
        db: AsyncSession,
        session_id: int,
        progress_callback=None
    ) -> Dict[str, Any]:
        """
        Process all data from a research session.
        
        Args:
            db: Database session
            session_id: Research session ID
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dict with processing stats and output files
        """
        logger.info(f"[KnowledgeSynthesizer] Starting synthesis for session {session_id}")
        
        # Get session with brand
        result = await db.execute(
            select(ResearchSession)
            .options(selectinload(ResearchSession.brand))
            .options(selectinload(ResearchSession.insights))
            .where(ResearchSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        
        if not session:
            return {"error": f"Session {session_id} not found"}
        
        brand = session.brand
        brand_name = brand.name if brand else f"Session_{session_id}"
        
        # Create brand directory
        safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in brand_name)
        brand_dir = self.output_dir / safe_name
        brand_dir.mkdir(parents=True, exist_ok=True)
        
        stats = {
            "session_id": session_id,
            "brand_name": brand_name,
            "started_at": datetime.now().isoformat(),
            "items_processed": 0,
            "items_by_type": {},
            "files_created": [],
            "errors": []
        }
        
        # Get all scraped data
        result = await db.execute(
            select(ScrapedData)
            .where(ScrapedData.session_id == session_id)
            .where(ScrapedData.content.isnot(None))
        )
        items = result.scalars().all()
        
        logger.info(f"[KnowledgeSynthesizer] Found {len(items)} items to process")
        
        # Group by processor type
        grouped = self._group_by_processor(items)
        
        # Process each group
        processed_data = {
            "reviews": [],
            "social": [],
            "discussions": [],
            "videos": [],
            "articles": [],
            "competitive": [],
            "brand": []
        }
        
        total_items = sum(len(items) for items in grouped.values())
        items_done = 0
        start_time = datetime.now()
        
        for processor_type, group_items in grouped.items():
            if progress_callback:
                progress_callback(f"Starting {processor_type}: {len(group_items)} items")
            
            logger.info(f"[KnowledgeSynthesizer] Processing {processor_type}: {len(group_items)} items")
            
            # Process in batches
            num_batches = (len(group_items) + self.batch_size - 1) // self.batch_size
            for batch_num, i in enumerate(range(0, len(group_items), self.batch_size), 1):
                batch = group_items[i:i + self.batch_size]
                batch_results = await self._process_batch(batch, processor_type)
                
                # Map to output category
                category = self._get_category(processor_type)
                processed_data[category].extend(batch_results)
                
                items_done += len(batch)
                stats["items_processed"] = items_done
                stats["items_by_type"][processor_type] = stats["items_by_type"].get(processor_type, 0) + len(batch)
                
                # Calculate estimated remaining time
                elapsed = (datetime.now() - start_time).total_seconds()
                if items_done > 0 and elapsed > 0:
                    items_per_sec = items_done / elapsed
                    remaining_items = total_items - items_done
                    est_remaining_sec = remaining_items / items_per_sec if items_per_sec > 0 else 0
                    est_remaining_min = int(est_remaining_sec / 60)
                    est_remaining_sec_mod = int(est_remaining_sec % 60)
                    
                    if progress_callback:
                        pct = int((items_done / total_items) * 100)
                        progress_callback(f"{processor_type} batch {batch_num}/{num_batches} - {pct}% done ({items_done}/{total_items}) - ~{est_remaining_min}m {est_remaining_sec_mod}s remaining")
        
        # Process Ad Library data from insights
        if session.insights:
            insight = session.insights[-1] if isinstance(session.insights, list) else session.insights
            ad_data = await self._process_ad_library(insight)
            processed_data["ads"] = ad_data
        
        # Generate output documents
        files = await self._generate_output_documents(brand_dir, brand_name, processed_data)
        stats["files_created"] = [str(f) for f in files]
        
        stats["completed_at"] = datetime.now().isoformat()
        
        # Save stats
        stats_file = brand_dir / "_processing_stats.json"
        stats_file.write_text(json.dumps(stats, indent=2, default=str))
        
        logger.info(f"[KnowledgeSynthesizer] Completed: {stats['items_processed']} items, {len(files)} files")
        
        return stats
    
    def _group_by_processor(self, items: List[ScrapedData]) -> Dict[str, List[ScrapedData]]:
        """Group items by processor type."""
        grouped = {}
        
        for item in items:
            source_type = item.source_type or 'other_review'
            
            # Determine processor type
            if source_type in ReviewProcessor.SOURCE_TYPES:
                key = 'review'
            elif source_type in SocialProcessor.SOURCE_TYPES:
                # Check if tiktok has video_analysis
                if source_type == 'tiktok' and item.video_analysis:
                    key = 'video'
                else:
                    key = 'social'
            elif source_type in DiscussionProcessor.SOURCE_TYPES:
                key = 'discussion'
            elif source_type in VideoProcessor.SOURCE_TYPES:
                key = 'video'
            elif source_type in ArticleProcessor.SOURCE_TYPES:
                key = 'article'
            elif source_type in CompetitiveProcessor.SOURCE_TYPES:
                key = 'competitive'
            elif source_type in BrandProcessor.SOURCE_TYPES:
                key = 'brand'
            else:
                key = 'review'  # Default to review
            
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(item)
        
        return grouped
    
    def _get_category(self, processor_type: str) -> str:
        """Map processor type to output category."""
        mapping = {
            'review': 'reviews',
            'social': 'social',
            'discussion': 'discussions',
            'video': 'videos',
            'article': 'articles',
            'competitive': 'competitive',
            'brand': 'brand'
        }
        return mapping.get(processor_type, 'reviews')
    
    async def _process_batch(
        self,
        items: List[ScrapedData],
        processor_type: str
    ) -> List[Dict[str, Any]]:
        """Process a batch of items with a SINGLE LLM call for efficiency."""
        if not items:
            return []
        
        # If not using LLM, do basic extraction (fast)
        if not self.use_llm:
            results = []
            processor = get_processor_for_source(items[0].source_type, llm_client=None)
            for idx, item in enumerate(items):
                print(f"        [{idx+1}/{len(items)}] {item.source_type} {item.id}...", end=" ", flush=True)
                processed = processor._basic_extraction(item.content or "", {"source_type": item.source_type})
                processed["item_id"] = item.id
                processed["source_type"] = item.source_type
                processed["raw_content"] = item.content[:500] if item.content else ""
                results.append(processed)
                print("OK (basic)")
            return results
        
        # BATCH LLM PROCESSING - send all items in one prompt
        print(f"        [BATCH] Processing {len(items)} {items[0].source_type} items in one call...", end=" ", flush=True)
        
        try:
            # Build batch prompt
            batch_prompt = self._build_batch_prompt(items, processor_type)
            
            # Single LLM call for all items
            import asyncio
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(self.llm_client.generate_content, batch_prompt),
                    timeout=60.0  # Longer timeout for batch
                )
                response_text = response.text
            except asyncio.TimeoutError:
                print("TIMEOUT")
                # Fallback to basic extraction
                return await self._fallback_basic_batch(items)
            
            # Parse batch response
            results = self._parse_batch_response(response_text, items)
            print(f"OK ({len(results)} items)")
            
            # Small delay between batches
            await asyncio.sleep(0.5)
            
            return results
            
        except Exception as e:
            print(f"FAILED: {e}")
            logger.error(f"Batch processing failed: {e}")
            return await self._fallback_basic_batch(items)
    
    def _build_batch_prompt(self, items: List[ScrapedData], processor_type: str) -> str:
        """Build a single prompt for batch processing."""
        source_type = items[0].source_type if items else "unknown"
        
        # Prepare items content
        items_text = []
        for i, item in enumerate(items):
            content = (item.content or "")[:800]  # Limit per item
            items_text.append(f"[ITEM_{i}]\nSource: {item.source_type}\nTitle: {item.title or 'N/A'}\nContent: {content}\n[/ITEM_{i}]")
        
        all_items = "\n\n".join(items_text)
        
        # Processor-specific extraction fields
        extraction_template = self._get_extraction_template(processor_type)
        
        return f"""Process these {len(items)} items from {source_type}. For EACH item, extract structured data.

{all_items}

For EACH item above, respond with a JSON array where each element corresponds to an item:
[
  {extraction_template},
  // ... one object per item
]

IMPORTANT:
- Return EXACTLY {len(items)} objects in the array, one for each [ITEM_N]
- Keep responses concise
- Return ONLY the JSON array, no other text"""
    
    def _get_extraction_template(self, processor_type: str) -> str:
        """Get extraction template based on processor type."""
        templates = {
            "review": '{"verbatim_quote": "key quote", "sentiment": "positive/negative/neutral", "key_themes": [], "pain_points": []}',
            "discussion": '{"main_topic": "topic", "brand_sentiment": "sentiment", "questions_asked": [], "verbatim_quotes": [], "objections_raised": []}',
            "social": '{"mention_type": "organic/paid/ugc", "sentiment": "sentiment", "key_message": "main point"}',
            "video": '{"executive_summary": "summary", "main_claims": [], "cta_mentioned": "cta"}',
            "article": '{"article_type": "type", "brand_mentions": [], "key_claims": []}',
            "competitive": '{"competitors_mentioned": [], "brand_advantages": [], "brand_disadvantages": []}',
            "brand": '{"value_propositions": [], "product_features": [], "target_audience_signals": []}'
        }
        return templates.get(processor_type, templates["review"])
    
    def _parse_batch_response(self, response: str, items: List[ScrapedData]) -> List[Dict[str, Any]]:
        """Parse batch LLM response into individual results."""
        import json
        import re
        
        results = []
        
        try:
            # Try to extract JSON array
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                parsed = json.loads(json_match.group())
                
                if isinstance(parsed, list):
                    for i, item in enumerate(items):
                        if i < len(parsed):
                            result = parsed[i] if isinstance(parsed[i], dict) else {}
                        else:
                            result = {}
                        
                        result["item_id"] = item.id
                        result["source_type"] = item.source_type
                        result["raw_content"] = item.content[:500] if item.content else ""
                        result["processed"] = True
                        results.append(result)
                    return results
        except json.JSONDecodeError:
            pass
        
        # Fallback: create basic results
        for item in items:
            results.append({
                "item_id": item.id,
                "source_type": item.source_type,
                "raw_content": item.content[:500] if item.content else "",
                "processed": False,
                "parse_error": True
            })
        
        return results
    
    async def _fallback_basic_batch(self, items: List[ScrapedData]) -> List[Dict[str, Any]]:
        """Fallback to basic extraction for failed batch."""
        results = []
        processor = get_processor_for_source(items[0].source_type if items else 'other_review', llm_client=None)
        
        for item in items:
            processed = processor._basic_extraction(item.content or "", {"source_type": item.source_type})
            processed["item_id"] = item.id
            processed["source_type"] = item.source_type
            processed["raw_content"] = item.content[:500] if item.content else ""
            results.append(processed)
        
        return results
    
    async def _process_ad_library(self, insight: Insight) -> List[Dict[str, Any]]:
        """Process Ad Library data from insights."""
        results = []
        
        processor = AdLibraryProcessor(llm_client=self.llm_client if self.use_llm else None)
        
        # Process brand ads
        if insight.ad_library_data:
            try:
                processed = await processor.process_ad_data(
                    insight.ad_library_data,
                    is_competitor=False
                )
                processed["ad_source"] = "brand"
                results.append(processed)
            except Exception as e:
                logger.error(f"Error processing ad library: {e}")
        
        # Process competitor ads
        if insight.competitor_ads_data:
            comp_data = insight.competitor_ads_data
            if isinstance(comp_data, list):
                for comp_ad in comp_data:
                    try:
                        comp_name = comp_ad.get('competitor_name', 'Unknown') if isinstance(comp_ad, dict) else 'Unknown'
                        processed = await processor.process_ad_data(
                            comp_ad,
                            is_competitor=True,
                            competitor_name=comp_name
                        )
                        processed["ad_source"] = "competitor"
                        results.append(processed)
                    except Exception as e:
                        logger.error(f"Error processing competitor ad: {e}")
        
        return results
    
    async def _generate_output_documents(
        self,
        brand_dir: Path,
        brand_name: str,
        processed_data: Dict[str, List]
    ) -> List[Path]:
        """Generate structured documents for AnythingLLM."""
        files = []
        
        # 1. Reviews Synthesis
        if processed_data.get("reviews"):
            file_path = brand_dir / "01_reviews_synthesis.md"
            content = self._generate_reviews_doc(brand_name, processed_data["reviews"])
            file_path.write_text(content, encoding='utf-8')
            files.append(file_path)
        
        # 2. Social Mentions
        if processed_data.get("social"):
            file_path = brand_dir / "02_social_mentions.md"
            content = self._generate_social_doc(brand_name, processed_data["social"])
            file_path.write_text(content, encoding='utf-8')
            files.append(file_path)
        
        # 3. Discussions Insights (Reddit, Forums)
        if processed_data.get("discussions"):
            file_path = brand_dir / "03_discussions_insights.md"
            content = self._generate_discussions_doc(brand_name, processed_data["discussions"])
            file_path.write_text(content, encoding='utf-8')
            files.append(file_path)
        
        # 4. Video Transcripts
        if processed_data.get("videos"):
            file_path = brand_dir / "04_video_transcripts.md"
            content = self._generate_videos_doc(brand_name, processed_data["videos"])
            file_path.write_text(content, encoding='utf-8')
            files.append(file_path)
        
        # 5. Articles & News
        if processed_data.get("articles"):
            file_path = brand_dir / "05_articles_news.md"
            content = self._generate_articles_doc(brand_name, processed_data["articles"])
            file_path.write_text(content, encoding='utf-8')
            files.append(file_path)
        
        # 6. Competitive Analysis
        if processed_data.get("competitive"):
            file_path = brand_dir / "06_competitive_analysis.md"
            content = self._generate_competitive_doc(brand_name, processed_data["competitive"])
            file_path.write_text(content, encoding='utf-8')
            files.append(file_path)
        
        # 7. Ad Library Analysis
        if processed_data.get("ads"):
            file_path = brand_dir / "07_ad_library_analysis.md"
            content = self._generate_ads_doc(brand_name, processed_data["ads"])
            file_path.write_text(content, encoding='utf-8')
            files.append(file_path)
        
        # 8. All Verbatim Quotes (consolidated)
        verbatims = self._extract_all_verbatims(processed_data)
        if verbatims:
            file_path = brand_dir / "08_verbatim_quotes.md"
            content = self._generate_verbatims_doc(brand_name, verbatims)
            file_path.write_text(content, encoding='utf-8')
            files.append(file_path)
        
        return files
    
    def _generate_reviews_doc(self, brand_name: str, reviews: List[Dict]) -> str:
        """Generate reviews synthesis document."""
        content = f"# {brand_name} - Customer Reviews Synthesis\n\n"
        content += f"Total reviews processed: {len(reviews)}\n\n"
        
        # Group by sentiment
        positive = [r for r in reviews if r.get('sentiment') == 'positive']
        negative = [r for r in reviews if r.get('sentiment') == 'negative']
        neutral = [r for r in reviews if r.get('sentiment') not in ['positive', 'negative']]
        
        content += f"## Sentiment Distribution\n"
        content += f"- Positive: {len(positive)}\n"
        content += f"- Negative: {len(negative)}\n"
        content += f"- Neutral: {len(neutral)}\n\n"
        
        content += "## Top Positive Reviews\n\n"
        for r in positive[:20]:
            quote = r.get('verbatim_quote') or r.get('raw_content') or ''
            quote = quote[:300] if quote else 'No quote available'
            source = r.get('source_type', 'unknown')
            content += f"### From {source}\n> \"{quote}\"\n\n"
        
        content += "## Pain Points Mentioned\n\n"
        all_pain_points = []
        for r in reviews:
            all_pain_points.extend(r.get('pain_points', []))
        for pp in list(set(all_pain_points))[:20]:
            content += f"- {pp}\n"
        
        return content
    
    def _generate_social_doc(self, brand_name: str, social: List[Dict]) -> str:
        """Generate social mentions document."""
        content = f"# {brand_name} - Social Media Mentions\n\n"
        content += f"Total mentions: {len(social)}\n\n"
        
        for s in social[:50]:
            source = s.get('source_type', 'social')
            msg = s.get('key_message') or s.get('content_snippet', '')[:200]
            sentiment = s.get('sentiment', 'neutral')
            content += f"## {source.title()} ({sentiment})\n{msg}\n\n"
        
        return content
    
    def _generate_discussions_doc(self, brand_name: str, discussions: List[Dict]) -> str:
        """Generate discussions document."""
        content = f"# {brand_name} - Community Discussions\n\n"
        content += f"Total discussions analyzed: {len(discussions)}\n\n"
        
        # Extract key insights
        all_questions = []
        all_objections = []
        all_recommendations = []
        
        for d in discussions:
            all_questions.extend(d.get('questions_asked', []))
            all_objections.extend(d.get('objections_raised', []))
            all_recommendations.extend(d.get('recommendations_given', []))
        
        content += "## Common Questions Asked\n"
        for q in list(set(all_questions))[:15]:
            content += f"- {q}\n"
        
        content += "\n## Objections & Concerns\n"
        for o in list(set(all_objections))[:15]:
            content += f"- {o}\n"
        
        content += "\n## Key Discussion Quotes\n"
        for d in discussions[:30]:
            quotes = d.get('verbatim_quotes', [])
            for q in quotes[:2]:
                content += f"> \"{q}\"\n\n"
        
        return content
    
    def _generate_videos_doc(self, brand_name: str, videos: List[Dict]) -> str:
        """Generate video transcripts document."""
        content = f"# {brand_name} - Video Content\n\n"
        content += f"Total videos: {len(videos)}\n\n"
        
        for v in videos:
            title = v.get('executive_summary', 'Video')
            content += f"## {title}\n\n"
            
            # Key claims
            claims = v.get('main_claims', [])
            if claims:
                content += "**Key Claims:**\n"
                for c in claims:
                    content += f"- {c}\n"
                content += "\n"
            
            # Transcript
            transcript = v.get('full_transcript') or v.get('transcript_snippet', '')
            if transcript:
                content += f"**Transcript:**\n{transcript[:2000]}\n\n"
            
            content += "---\n\n"
        
        return content
    
    def _generate_articles_doc(self, brand_name: str, articles: List[Dict]) -> str:
        """Generate articles document."""
        content = f"# {brand_name} - News & Articles\n\n"
        content += f"Total articles: {len(articles)}\n\n"
        
        for a in articles:
            title = a.get('title') or a.get('main_takeaway', 'Article')
            article_type = a.get('article_type', 'unknown')
            content += f"## {title}\n"
            content += f"*Type: {article_type}*\n\n"
            
            # Brand mentions
            mentions = a.get('brand_mentions', [])
            for m in mentions:
                if isinstance(m, dict):
                    content += f"- {m.get('context', '')} ({m.get('sentiment', '')})\n"
            
            content += "\n"
        
        return content
    
    def _generate_competitive_doc(self, brand_name: str, competitive: List[Dict]) -> str:
        """Generate competitive analysis document."""
        content = f"# {brand_name} - Competitive Analysis\n\n"
        
        all_competitors = []
        all_advantages = []
        all_disadvantages = []
        
        for c in competitive:
            all_competitors.extend(c.get('competitors_mentioned', []))
            all_advantages.extend(c.get('brand_advantages', []))
            all_disadvantages.extend(c.get('brand_disadvantages', []))
        
        content += "## Competitors Mentioned\n"
        for comp in list(set(all_competitors))[:20]:
            content += f"- {comp}\n"
        
        content += "\n## Our Advantages\n"
        for adv in list(set(all_advantages))[:15]:
            content += f"- {adv}\n"
        
        content += "\n## Areas to Improve\n"
        for dis in list(set(all_disadvantages))[:15]:
            content += f"- {dis}\n"
        
        return content
    
    def _generate_ads_doc(self, brand_name: str, ads: List[Dict]) -> str:
        """Generate ad library document."""
        content = f"# {brand_name} - Ad Library Analysis\n\n"
        
        brand_ads = [a for a in ads if a.get('ad_source') == 'brand' or a.get('ad_type') == 'brand_ad']
        competitor_ads = [a for a in ads if a.get('ad_source') == 'competitor' or a.get('ad_type') == 'competitor_ad']
        
        content += f"## Brand Ads ({len(brand_ads)})\n\n"
        for ad in brand_ads:
            # Use correct field names from scraper
            ad_copy = ad.get('ad_copy') or ad.get('headline', 'N/A')
            cta = ad.get('cta', 'N/A')
            has_video = ad.get('has_video', False)
            creative_analysis = ad.get('creative_analysis', {})
            hook = creative_analysis.get('hook_type', 'N/A') if isinstance(creative_analysis, dict) else 'N/A'
            
            content += f"### Ad\n"
            content += f"- **Ad Copy:** {ad_copy[:200]}{'...' if len(str(ad_copy)) > 200 else ''}\n"
            content += f"- **CTA:** {cta}\n"
            content += f"- **Format:** {'Video' if has_video else 'Image'}\n"
            content += f"- **Hook Type:** {hook}\n\n"
        
        content += f"## Competitor Ads ({len(competitor_ads)})\n\n"
        for ad in competitor_ads:
            comp_name = ad.get('competitor_name') or ad.get('brand_name', 'Unknown')
            ad_copy = ad.get('ad_copy') or ad.get('headline', 'N/A')
            cta = ad.get('cta', 'N/A')
            discount = ad.get('discount_code', '')
            has_video = ad.get('has_video', False)
            creative_analysis = ad.get('creative_analysis', {})
            
            content += f"### COMPETITOR: {comp_name}\n"
            content += f"- **Ad Copy:** {ad_copy[:200]}{'...' if len(str(ad_copy)) > 200 else ''}\n"
            content += f"- **CTA:** {cta}\n"
            if discount:
                content += f"- **Discount:** {discount}\n"
            content += f"- **Format:** {'Video' if has_video else 'Image'}\n"
            
            # Extract insights from creative_analysis
            if isinstance(creative_analysis, dict):
                hook = creative_analysis.get('hook_type', '')
                emotional = creative_analysis.get('emotional_triggers', [])
                if hook:
                    content += f"- **Hook Strategy:** {hook}\n"
                if emotional:
                    content += f"- **Emotional Triggers:** {', '.join(emotional[:3])}\n"
            content += "\n"
        
        return content
    
    def _extract_all_verbatims(self, processed_data: Dict) -> List[Dict]:
        """Extract all verbatim quotes from processed data."""
        verbatims = []
        
        for category, items in processed_data.items():
            for item in items:
                quote = item.get('verbatim_quote')
                if quote and len(quote) > 20:
                    verbatims.append({
                        "quote": quote,
                        "source": item.get('source_type', category),
                        "sentiment": item.get('sentiment', 'neutral')
                    })
                
                # Also get quotes from discussions
                quotes_list = item.get('verbatim_quotes', [])
                for q in quotes_list:
                    if isinstance(q, str) and len(q) > 20:
                        verbatims.append({
                            "quote": q,
                            "source": item.get('source_type', category),
                            "sentiment": "neutral"
                        })
        
        return verbatims
    
    def _generate_verbatims_doc(self, brand_name: str, verbatims: List[Dict]) -> str:
        """Generate consolidated verbatim quotes document."""
        content = f"# {brand_name} - All Verbatim Customer Quotes\n\n"
        content += f"Total quotes: {len(verbatims)}\n\n"
        content += "This document contains exact customer quotes for reference.\n\n"
        
        # Group by sentiment
        positive = [v for v in verbatims if v.get('sentiment') == 'positive']
        negative = [v for v in verbatims if v.get('sentiment') == 'negative']
        other = [v for v in verbatims if v.get('sentiment') not in ['positive', 'negative']]
        
        content += "## Positive Quotes\n\n"
        for v in positive[:50]:
            content += f"> \"{v['quote']}\"\n> *Source: {v['source']}*\n\n"
        
        content += "## Critical Quotes\n\n"
        for v in negative[:30]:
            content += f"> \"{v['quote']}\"\n> *Source: {v['source']}*\n\n"
        
        content += "## Other Quotes\n\n"
        for v in other[:30]:
            content += f"> \"{v['quote']}\"\n> *Source: {v['source']}*\n\n"
        
        return content


# Singleton
_synthesizer: Optional[KnowledgeSynthesizer] = None

def get_knowledge_synthesizer(
    output_dir: str = "knowledge_base_processed",
    use_llm: bool = True
) -> KnowledgeSynthesizer:
    """Get or create Knowledge Synthesizer instance."""
    global _synthesizer
    if _synthesizer is None:
        _synthesizer = KnowledgeSynthesizer(output_dir=output_dir, use_llm=use_llm)
    return _synthesizer
