# -*- coding: utf-8 -*-
"""
Research API - Data access layer for chat and other consumers.
Provides stable, type-safe access to research data.
NEVER throws errors - always returns valid response with status.
"""

import json
import logging
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text

from ..models import Brand, ResearchSession, ScrapedData

logging.basicConfig(level=logging.INFO, stream=sys.stdout, force=True)
logger = logging.getLogger(__name__)


@dataclass
class ResearchPack:
    """Stable research context - NEVER null on required fields."""
    research_id: int
    status: str  # "ready" | "running" | "partial" | "failed" | "not_found"
    brand_info: Dict[str, Any]
    stats: Dict[str, Any]
    insights_summary: Dict[str, Any]
    missing_fields: List[str]
    updated_at: str
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def to_context_string(self) -> str:
        """Convert to LLM-friendly context string."""
        parts = []
        
        # Brand info
        bi = self.brand_info
        parts.append(f"**Brand**: {bi.get('name', 'Unknown')}")
        parts.append(f"**Sector**: {bi.get('sector', 'N/A')}")
        if bi.get('description'):
            parts.append(f"**Description**: {bi['description'][:300]}")
        
        # Stats
        st = self.stats
        parts.append(f"\n**Data Stats**:")
        parts.append(f"- Total data points: {st.get('total_items', 0)}")
        parts.append(f"- Sources: {', '.join(st.get('sources', []))}")
        if st.get('sentiment_avg'):
            parts.append(f"- Avg sentiment: {st['sentiment_avg']:.2f}")
        
        # Insights summary
        ins = self.insights_summary
        if ins.get('pain_points'):
            parts.append(f"\n**Top Pain Points**: {', '.join(str(p)[:80] for p in ins['pain_points'][:5])}")
        if ins.get('value_props'):
            parts.append(f"**Value Props**: {', '.join(str(v)[:80] for v in ins['value_props'][:5])}")
        if ins.get('icps'):
            parts.append(f"**ICPs**: {', '.join(str(i)[:50] for i in ins['icps'][:3])}")
        
        # Verbatim Quotes (NEW)
        if ins.get('verbatim_quotes'):
            parts.append("\n**Customer Quotes:**")
            for q in ins['verbatim_quotes'][:5]:
                if isinstance(q, dict):
                    quote = q.get('quote', q.get('text', str(q)))[:150]
                    source = q.get('source', '')
                    parts.append(f'- "{quote}" [{source}]' if source else f'- "{quote}"')
                else:
                    parts.append(f'- "{str(q)[:150]}"')
        
        # Customer Language (NEW)
        if ins.get('customer_language'):
            lang = ins['customer_language'][:5]
            parts.append(f"\n**Customer Language**: {', '.join(str(l)[:40] for l in lang)}")
        
        # TikTok Insights (NEW)
        if ins.get('tiktok_trends'):
            tiktok = ins['tiktok_trends']
            segment = tiktok.get('segment_analysis', {}) if isinstance(tiktok, dict) else {}
            if segment:
                parts.append("\n**TikTok Insights:**")
                agg = segment.get('aggregated', {})
                if agg.get('trending_formats'):
                    parts.append(f"- Trending formats: {', '.join(str(f)[:30] for f in agg['trending_formats'][:3])}")
                if agg.get('recommended_hook_types'):
                    parts.append(f"- Best hooks: {', '.join(str(h)[:30] for h in agg['recommended_hook_types'][:3])}")
        
        # Instagram Brand (NEW)
        if ins.get('instagram_brand_presence'):
            ig = ins['instagram_brand_presence']
            if isinstance(ig, dict):
                parts.append("\n**Instagram Brand:**")
                if ig.get('brand_voice'):
                    voice = ig['brand_voice']
                    if isinstance(voice, dict):
                        parts.append(f"- Voice: {voice.get('tone', str(voice)[:50])}")
                    else:
                        parts.append(f"- Voice: {str(voice)[:80]}")
                if ig.get('content_pillars'):
                    parts.append(f"- Pillars: {', '.join(str(p)[:30] for p in ig['content_pillars'][:3])}")
        
        # Ad Library Data (if available)
        ad_patterns = ins.get('ad_creative_patterns', {})
        if ad_patterns and ad_patterns.get('total_analyzed', 0) > 0:
            parts.append(f"\n**Ad Library Analysis** ({ad_patterns.get('total_analyzed', 0)} ads analyzed):")
            # Frameworks
            if ad_patterns.get('frameworks'):
                top_frameworks = sorted(ad_patterns['frameworks'].items(), key=lambda x: x[1], reverse=True)[:3]
                parts.append(f"- Top Frameworks: {', '.join([f'{k} ({v})' for k, v in top_frameworks])}")
            # Hook types
            if ad_patterns.get('hook_types'):
                top_hooks = sorted(ad_patterns['hook_types'].items(), key=lambda x: x[1], reverse=True)[:3]
                parts.append(f"- Top Hook Types: {', '.join([f'{k} ({v})' for k, v in top_hooks])}")
            # Avg scores
            if ad_patterns.get('avg_hook_strength'):
                parts.append(f"- Avg Hook Strength: {ad_patterns['avg_hook_strength']:.1f}/5")
            if ad_patterns.get('avg_effectiveness'):
                parts.append(f"- Avg Effectiveness: {ad_patterns['avg_effectiveness']:.1f}/5")
            # Top transcriptions
            top_trans = ad_patterns.get('top_transcriptions', [])[:3]
            if top_trans:
                parts.append("\n**Top Ad Transcriptions:**")
                for i, t in enumerate(top_trans, 1):
                    text = t.get('text', '')[:200]
                    score = t.get('effectiveness', 0)
                    parts.append(f"{i}. (effectiveness: {score}/5) \"{text}...\"")
        
        # Cross-Source Insights
        cross_source = ins.get('cross_source_insights', {})
        if cross_source:
            parts.append("\n**Cross-Source Validated Insights:**")
            # Validated pain points
            vpp = cross_source.get('ai_validated_pain_points', cross_source.get('validated_pain_points', []))
            if vpp:
                parts.append("Validated Pain Points (confirmed across multiple sources):")
                for pp in vpp[:5]:
                    if isinstance(pp, dict):
                        conf = f" ({pp.get('confidence', 0)*100:.0f}% confidence)" if pp.get('confidence') else ""
                        srcs = f" [{', '.join(pp.get('sources', [])[:3])}]" if pp.get('sources') else ""
                        parts.append(f"- {pp.get('pain_point', pp)}{conf}{srcs}")
                    else:
                        parts.append(f"- {pp}")
            # Strategic recommendations
            recs = cross_source.get('strategic_recommendations', [])
            if recs:
                parts.append("Strategic Recommendations:")
                for r in recs[:3]:
                    parts.append(f"- {str(r)[:120]}")
            # Messaging gaps
            gaps = cross_source.get('messaging_gaps', [])
            if gaps:
                parts.append("Messaging Gaps (what customers say vs. what brand says):")
                for g in gaps[:3]:
                    if isinstance(g, dict):
                        parts.append(f"- {g.get('gap', g)}")
                    else:
                        parts.append(f"- {g}")
        
        # Competitive Intelligence
        comp_matrix = ins.get('competitive_matrix', {})
        if comp_matrix:
            parts.append("\n**Competitive Matrix:**")
            if comp_matrix.get('our_strengths'):
                parts.append(f"- Our strengths: {', '.join(str(s)[:50] for s in comp_matrix['our_strengths'][:3])}")
            if comp_matrix.get('our_weaknesses'):
                parts.append(f"- Our weaknesses: {', '.join(str(w)[:50] for w in comp_matrix['our_weaknesses'][:3])}")
            if comp_matrix.get('positioning_recommendation'):
                parts.append(f"- Positioning: {str(comp_matrix['positioning_recommendation'])[:120]}")
        
        # Hooks Library Summary
        hooks = ins.get('hooks_library', {})
        if hooks and hooks.get('total_hooks', 0) > 0:
            parts.append(f"\n**Hooks Library** ({hooks.get('total_hooks', 0)} hooks generated):")
            top_types = hooks.get('type_distribution', {})
            if top_types:
                sorted_types = sorted(top_types.items(), key=lambda x: x[1], reverse=True)[:3]
                parts.append(f"- Top types: {', '.join([f'{k} ({v})' for k, v in sorted_types])}")
            all_hooks = hooks.get('all_hooks', [])
            if all_hooks:
                parts.append("- Best hooks:")
                top = sorted(all_hooks, key=lambda x: x.get('strength_score', 0), reverse=True)[:3]
                for h in top:
                    parts.append(f"  • \"{h.get('hook_text', '')}\" (strength: {h.get('strength_score', 0)}/5)")
        
        # Sentiment Breakdown
        if ins.get('sentiment_by_source'):
            parts.append("\n**Sentiment by Source (RoBERTa ML analysis):")
            for src, stats in sorted(ins['sentiment_by_source'].items(), key=lambda x: x[1].get('total', 0), reverse=True)[:5]:
                parts.append(f"- {src}: {stats.get('positive',0)} pos, {stats.get('negative',0)} neg, {stats.get('neutral',0)} neu (avg: {stats.get('avg_score',0):+.3f})")
        
        # Status
        if self.status != "ready":
            parts.append(f"\n⚠️ Research status: {self.status}")
            if self.missing_fields:
                parts.append(f"Missing: {', '.join(self.missing_fields)}")
        
        return "\n".join(parts)


class ResearchAPI:
    """
    Unified API for accessing research data.
    All methods return valid responses - never throw on missing data.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_research_pack(self, research_id: int) -> ResearchPack:
        """
        Get complete research pack for a session.
        NEVER fails - returns status: "not_found" if missing.
        """
        from sqlalchemy.orm import selectinload
        
        logger.info(f"[ResearchAPI] get_research_pack called for id={research_id}")
        try:
            # Get session with relationships
            result = await self.db.execute(
                select(ResearchSession)
                .options(selectinload(ResearchSession.brand))
                .options(selectinload(ResearchSession.insights))
                .where(ResearchSession.id == research_id)
            )
            session = result.scalar_one_or_none()
            
            logger.info(f"[ResearchAPI] Session found: {session is not None}")
            
            if not session:
                logger.warning(f"[ResearchAPI] Session {research_id} not found")
                return ResearchPack(
                    research_id=research_id,
                    status="not_found",
                    brand_info={"name": "Unknown", "sector": "Unknown"},
                    stats={"total_items": 0, "sources": []},
                    insights_summary={},
                    missing_fields=["session"],
                    updated_at=datetime.now().isoformat(),
                    error=f"Session {research_id} not found"
                )
            
            # Get brand info from related Brand object
            brand = session.brand
            brand_info = {}
            if brand:
                brand_info = {
                    'name': brand.name,
                    'website_url': brand.website_url,
                    'description': brand.description or '',
                    'sector': brand.sector or '',
                    'vertical': brand.vertical or '',
                    'tagline': brand.tagline or '',
                }
                logger.info(f"[ResearchAPI] Brand found: {brand.name}")
            else:
                logger.warning(f"[ResearchAPI] No brand linked to session {research_id}")
            
            # Get insights from related Insight objects
            insights = {}
            ad_creative_patterns = {}
            if session.insights and len(session.insights) > 0:
                # Take the most recent insight
                insight_obj = session.insights[-1]
                insights = {
                    # Core insights
                    'pain_points': insight_obj.pain_points or [],
                    'value_props': insight_obj.value_props or [],
                    'icps': insight_obj.icps or [],
                    'objections': insight_obj.objections or [],
                    'messaging_angles': insight_obj.messaging_angles or [],
                    'recommended_hooks': insight_obj.recommended_hooks or [],
                    
                    # Customer voice data (NEW)
                    'verbatim_quotes': insight_obj.verbatim_quotes or [],
                    'customer_language': insight_obj.customer_language or [],
                    'customer_desires': insight_obj.customer_desires or [],
                    
                    # Platform-specific insights (NEW)
                    'tiktok_trends': insight_obj.tiktok_trends or {},
                    'instagram_brand_presence': insight_obj.instagram_brand_presence or {},
                    
                    # Hooks library (NEW)
                    'hooks_library': insight_obj.hooks_library or {},
                    
                    # Cross-source validated insights
                    'cross_source_insights': insight_obj.cross_source_insights or {},
                    
                    # Competitive intelligence
                    'competitive_matrix': insight_obj.competitive_matrix or {},
                    'swot_analysis': insight_obj.swot_analysis or {},
                }
                # Extract Ad Library data
                ad_creative_patterns = insight_obj.ad_creative_patterns or {}
                logger.info(f"[ResearchAPI] Insights found: {len(insights.get('pain_points', []))} pain points")
                logger.info(f"[ResearchAPI] Ad patterns found: {ad_creative_patterns.get('total_analyzed', 0)} ads analyzed")
            else:
                logger.warning(f"[ResearchAPI] No insights for session {research_id}")
            
            logger.info(f"[ResearchAPI] brand_info keys: {list(brand_info.keys()) if brand_info else 'empty'}")
            logger.info(f"[ResearchAPI] insights keys: {list(insights.keys()) if insights else 'empty'}")
            
            # Track missing fields
            missing = []
            if not brand_info.get('name'):
                missing.append('brand_name')
            if not insights:
                missing.append('insights')
            
            # Get stats from scraped_data
            stats = await self._get_stats(research_id)
            logger.info(f"[ResearchAPI] Stats: total_items={stats.get('total_items', 0)}, sources={stats.get('sources', [])}")
            
            # Determine status
            if session.status == "completed" and not missing:
                status = "ready"
            elif session.status == "in_progress":
                status = "running"
            elif session.status == "failed":
                status = "failed"
            elif missing:
                status = "partial"
            else:
                status = session.status or "unknown"
            
            # Build insights summary with Ad Library data + new fields
            insights_summary = {
                "pain_points": self._extract_list(insights, 'pain_points', 5),
                "value_props": self._extract_list(insights, 'value_props', 5),
                "icps": self._extract_icp_names(insights.get('icps', [])),
                "objections": self._extract_objection_texts(insights.get('objections', [])),
                "ad_creative_patterns": ad_creative_patterns,
                # NEW: Customer voice data
                "verbatim_quotes": insights.get('verbatim_quotes', [])[:10],
                "customer_language": insights.get('customer_language', [])[:8],
                # NEW: Platform insights
                "tiktok_trends": insights.get('tiktok_trends', {}),
                "instagram_brand_presence": insights.get('instagram_brand_presence', {}),
                # Cross-source insights + competitive
                "cross_source_insights": insights.get('cross_source_insights', {}),
                "competitive_matrix": insights.get('competitive_matrix', {}),
                "hooks_library": insights.get('hooks_library', {}),
            }
            
            return ResearchPack(
                research_id=research_id,
                status=status,
                brand_info={
                    "name": brand_info.get('name', 'Unknown Brand'),
                    "sector": brand_info.get('sector', 'Unknown'),
                    "vertical": brand_info.get('vertical', ''),
                    "description": brand_info.get('description', ''),
                    "website": brand_info.get('website_url', ''),
                },
                stats=stats,
                insights_summary=insights_summary,
                missing_fields=missing,
                updated_at=datetime.now().isoformat()
            )
            
        except Exception as e:
            return ResearchPack(
                research_id=research_id,
                status="error",
                brand_info={"name": "Error", "sector": "Unknown"},
                stats={"total_items": 0, "sources": []},
                insights_summary={},
                missing_fields=["all"],
                updated_at=datetime.now().isoformat(),
                error=str(e)
            )
    
    async def search_text(
        self,
        research_id: int,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search scraped text data.
        Returns list of matching items with source info.
        """
        try:
            filters = filters or {}
            
            # Build query
            stmt = select(ScrapedData).where(
                ScrapedData.session_id == research_id,
                ScrapedData.content.isnot(None)
            )
            
            # Apply filters
            if filters.get('source_type'):
                stmt = stmt.where(ScrapedData.source_type == filters['source_type'])
            if filters.get('sentiment'):
                stmt = stmt.where(ScrapedData.sentiment == filters['sentiment'])
            
            # Text search (simple LIKE for now)
            if query:
                stmt = stmt.where(ScrapedData.content.ilike(f"%{query}%"))
            
            stmt = stmt.limit(limit)
            
            result = await self.db.execute(stmt)
            items = result.scalars().all()
            
            return [
                {
                    "id": item.id,
                    "content": (item.content or "")[:500],
                    "source_type": item.source_type,
                    "source_url": item.source_url,
                    "sentiment": item.sentiment,
                    "author": item.author,
                    "likes": item.likes,
                }
                for item in items
            ]
            
        except Exception as e:
            return [{"error": str(e)}]
    
    async def query_metrics(
        self,
        research_id: int,
        metric: str,
        group_by: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run analytics query on research data.
        Returns aggregated metrics.
        """
        try:
            filters = filters or {}
            
            if metric == "count_by_source":
                result = await self.db.execute(
                    select(
                        ScrapedData.source_type,
                        func.count(ScrapedData.id).label('count')
                    )
                    .where(ScrapedData.session_id == research_id)
                    .group_by(ScrapedData.source_type)
                )
                rows = result.fetchall()
                return {
                    "metric": metric,
                    "data": {row[0]: row[1] for row in rows},
                    "total": sum(row[1] for row in rows)
                }
            
            elif metric == "sentiment_by_source":
                result = await self.db.execute(
                    select(
                        ScrapedData.source_type,
                        ScrapedData.sentiment,
                        func.count(ScrapedData.id).label('count')
                    )
                    .where(ScrapedData.session_id == research_id)
                    .where(ScrapedData.sentiment.isnot(None))
                    .group_by(ScrapedData.source_type, ScrapedData.sentiment)
                )
                rows = result.fetchall()
                data = {}
                for source, sentiment, count in rows:
                    if source not in data:
                        data[source] = {}
                    data[source][sentiment] = count
                return {"metric": metric, "data": data}
            
            elif metric == "top_authors":
                result = await self.db.execute(
                    select(
                        ScrapedData.author,
                        func.count(ScrapedData.id).label('count'),
                        func.sum(ScrapedData.likes).label('total_likes')
                    )
                    .where(ScrapedData.session_id == research_id)
                    .where(ScrapedData.author.isnot(None))
                    .group_by(ScrapedData.author)
                    .order_by(func.count(ScrapedData.id).desc())
                    .limit(10)
                )
                rows = result.fetchall()
                return {
                    "metric": metric,
                    "data": [{"author": r[0], "posts": r[1], "likes": r[2] or 0} for r in rows]
                }
            
            else:
                return {"metric": metric, "error": f"Unknown metric: {metric}"}
                
        except Exception as e:
            return {"metric": metric, "error": str(e)}
    
    async def get_sample_quotes(
        self,
        research_id: int,
        limit: int = 10,
        sentiment: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get sample customer quotes for context."""
        try:
            stmt = select(ScrapedData).where(
                ScrapedData.session_id == research_id,
                ScrapedData.content.isnot(None)
            )
            
            if sentiment:
                stmt = stmt.where(ScrapedData.sentiment == sentiment)
            
            # Order by engagement
            stmt = stmt.order_by(ScrapedData.likes.desc().nullslast()).limit(limit)
            
            result = await self.db.execute(stmt)
            items = result.scalars().all()
            
            return [
                {
                    "quote": (item.content or "")[:300],
                    "source": item.source_type,
                    "sentiment": item.sentiment,
                    "likes": item.likes or 0,
                }
                for item in items
            ]
        except Exception as e:
            return []
    
    # === Helper methods ===
    
    def _parse_json_field(self, field: Any, default: Any) -> Any:
        """Safely parse a field that might be JSON string or dict."""
        if field is None:
            return default
        if isinstance(field, dict):
            return field
        if isinstance(field, str):
            try:
                return json.loads(field)
            except:
                return default
        return default
    
    async def _get_stats(self, research_id: int) -> Dict[str, Any]:
        """Get basic stats for research."""
        try:
            # Count by source
            result = await self.db.execute(
                select(
                    ScrapedData.source_type,
                    func.count(ScrapedData.id).label('count')
                )
                .where(ScrapedData.session_id == research_id)
                .group_by(ScrapedData.source_type)
            )
            by_source = {row[0]: row[1] for row in result.fetchall()}
            
            # Avg sentiment
            result = await self.db.execute(
                select(func.avg(ScrapedData.sentiment_score))
                .where(ScrapedData.session_id == research_id)
                .where(ScrapedData.sentiment_score.isnot(None))
            )
            sentiment_avg = result.scalar()
            
            return {
                "total_items": sum(by_source.values()),
                "by_source": by_source,
                "sources": list(by_source.keys()),
                "sentiment_avg": float(sentiment_avg) if sentiment_avg else None
            }
        except:
            return {"total_items": 0, "sources": [], "by_source": {}}
    
    def _extract_list(self, data: Dict, key: str, limit: int) -> List[str]:
        """Extract list of strings from insights."""
        items = data.get(key, [])
        if not items:
            return []
        return [str(item)[:100] for item in items[:limit]]
    
    def _extract_icp_names(self, icps: List) -> List[str]:
        """Extract ICP names."""
        names = []
        for icp in icps[:5]:
            if isinstance(icp, dict):
                names.append(icp.get('name', 'Unknown ICP'))
            elif isinstance(icp, str):
                names.append(icp)
        return names
    
    def _extract_objection_texts(self, objections: List) -> List[str]:
        """Extract objection texts."""
        texts = []
        for obj in objections[:5]:
            if isinstance(obj, dict):
                texts.append(obj.get('objection', str(obj)))
            elif isinstance(obj, str):
                texts.append(obj)
        return texts

# Trigger reload
