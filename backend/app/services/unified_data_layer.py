"""
Unified Data Layer - Phase 8

Capa de datos unificada que todos los generadores consumen.
Normaliza y agrega toda la data de todas las fuentes.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from collections import defaultdict
import json


class UnifiedDataLayer:
    """
    Unified data layer that all generators consume.
    
    Aggregates data from:
    - Scraped data (all sources)
    - Video analysis (IMA dimensions)
    - Cross-source insights
    - Ad library intelligence
    - Brand context
    
    Usage:
        unified = UnifiedDataLayer()
        data = unified.build(
            brand=brand_dict,
            scraped_data=scraped_data_list,
            insights=insights_dict,
            video_analyses=video_list
        )
        scripts = await script_generator.generate(data)
    """
    
    def build(
        self,
        brand: Dict[str, Any],
        scraped_data: List[Dict[str, Any]] = None,
        insights: Dict[str, Any] = None,
        video_analyses: List[Dict[str, Any]] = None,
        ad_library_data: Dict[str, Any] = None,
        competitor_ads: List[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Build unified data object from all sources.
        
        Args:
            brand: Brand information and DNA
            scraped_data: All scraped data items
            insights: Generated insights
            video_analyses: Video analysis results
            ad_library_data: Brand's ads from Ad Library
            competitor_ads: Competitor ad data
            
        Returns:
            Unified data dictionary with all normalized data
        """
        scraped_data = scraped_data or []
        insights = insights or {}
        video_analyses = video_analyses or []
        ad_library_data = ad_library_data or {}
        competitor_ads = competitor_ads or []
        
        return {
            # === Brand Context ===
            "brand": self._build_brand_context(brand),
            
            # === Voice of Customer (VoC) ===
            "voc": self._build_voc(scraped_data, insights),
            
            # === Video Intelligence ===
            "video_intelligence": self._build_video_intelligence(video_analyses),
            
            # === Cross-Source Insights ===
            "cross_source": self._build_cross_source(insights),
            
            # === Ad Intelligence ===
            "ad_intelligence": self._build_ad_intelligence(
                ad_library_data, competitor_ads, insights
            ),
            
            # === Computed/Derived ===
            "computed": self._build_computed(
                scraped_data, video_analyses, insights
            ),
            
            # === Data Coverage Metrics ===
            "coverage": self._build_coverage_metrics(
                scraped_data, video_analyses, insights
            ),
            
            # === Metadata ===
            "metadata": {
                "built_at": datetime.now(timezone.utc).isoformat() + "Z",
                "total_data_points": len(scraped_data),
                "video_count": len(video_analyses),
            }
        }
    
    def _build_brand_context(self, brand: Dict[str, Any]) -> Dict[str, Any]:
        """Build brand context section."""
        return {
            "name": brand.get("name", ""),
            "sector": brand.get("sector", ""),
            "vertical": brand.get("vertical", ""),
            "products": brand.get("products", []),
            "target_audience": brand.get("target_audience", ""),
            "description": brand.get("description", ""),
            "dna": {
                "colors": brand.get("brand_colors", []),
                "fonts": brand.get("fonts", []),
                "values": brand.get("brand_values", []),
                "aesthetic": brand.get("brand_aesthetic", []),
                "tone_of_voice": brand.get("tone_of_voice", []),
                "tagline": brand.get("tagline", ""),
            },
            "social_media": brand.get("social_media_urls", {}),
        }
    
    def _build_voc(
        self, 
        scraped_data: List[Dict[str, Any]], 
        insights: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build Voice of Customer section."""
        
        # Group snippets by source
        by_source = defaultdict(list)
        for item in scraped_data:
            source = item.get("source_type", "unknown")
            by_source[source].append({
                "content": item.get("content", ""),
                "title": item.get("title", ""),
                "sentiment": item.get("sentiment", "neutral"),
                "sentiment_score": item.get("sentiment_score", 0),
                "source_url": item.get("source_url", ""),
                "author": item.get("author", ""),
                "likes": item.get("likes", 0),
                "track": item.get("track", 1),
            })
        
        # Group by sentiment
        by_sentiment = defaultdict(list)
        for item in scraped_data:
            sentiment = item.get("sentiment", "neutral")
            if item.get("content"):
                by_sentiment[sentiment].append(item.get("content", "")[:200])
        
        # Extract verbatims
        verbatim_quotes = insights.get("verbatim_quotes", [])
        if not verbatim_quotes:
            # Generate from scraped data
            verbatim_quotes = self._extract_verbatims(scraped_data)
        
        return {
            "snippets_total": len(scraped_data),
            "by_source": dict(by_source),
            "by_sentiment": dict(by_sentiment),
            "verbatim_quotes": verbatim_quotes[:20],  # Top 20
            "customer_language": insights.get("customer_language", []),
            "market_pain_points": insights.get("market_pain_points", []),
            "customer_desires": insights.get("customer_desires", []),
        }
    
    def _extract_verbatims(
        self, 
        scraped_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract usable verbatim quotes from scraped data."""
        verbatims = []
        
        for item in scraped_data:
            content = item.get("content", "")
            if not content or len(content) < 20:
                continue
            
            # Prefer positive/negative sentiment
            sentiment = item.get("sentiment", "neutral")
            if sentiment in ["positive", "negative"]:
                verbatims.append({
                    "quote": content[:300],
                    "source": item.get("source_type", "unknown"),
                    "sentiment": sentiment,
                    "author": item.get("author", ""),
                    "engagement": item.get("likes", 0),
                })
        
        # Sort by engagement
        verbatims.sort(key=lambda x: x.get("engagement", 0), reverse=True)
        return verbatims[:20]
    
    def _build_video_intelligence(
        self, 
        video_analyses: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build video intelligence section with IMA dimensions."""
        
        if not video_analyses:
            return {
                "analyses": [],
                "frameworks": {},
                "emotions": {},
                "hooks": [],
                "transcriptions": [],
                "avg_hook_strength": 0,
            }
        
        # Aggregate frameworks
        frameworks = defaultdict(int)
        emotions = defaultdict(int)
        hooks = []
        transcriptions = []
        hook_strengths = []
        
        for va in video_analyses:
            # Framework
            fw = va.get("framework", "Unknown")
            if fw:
                frameworks[fw] += 1
            
            # Emotions
            emo = va.get("target_emotion") or va.get("emotion")
            if emo:
                emotions[emo] += 1
            
            # Hooks
            hook = va.get("hook") or va.get("opening_copy", "")
            if hook:
                hooks.append({
                    "text": hook,
                    "type": va.get("hook_type", ""),
                    "strength": va.get("hook_strength_1to5", 3),
                })
                strength = va.get("hook_strength_1to5", 3)
                if isinstance(strength, (int, float)):
                    hook_strengths.append(strength)
            
            # Transcriptions
            trans = va.get("transcription", "")
            if trans:
                transcriptions.append({
                    "text": trans[:500],
                    "framework": fw,
                    "effectiveness": va.get("effectiveness_score_1to5", 3),
                })
        
        avg_strength = sum(hook_strengths) / len(hook_strengths) if hook_strengths else 0
        
        return {
            "analyses": video_analyses,
            "frameworks": dict(frameworks),
            "emotions": dict(emotions),
            "hooks": hooks,
            "transcriptions": transcriptions[:10],  # Top 10
            "avg_hook_strength": round(avg_strength, 1),
            "total_analyzed": len(video_analyses),
        }
    
    def _build_cross_source(self, insights: Dict[str, Any]) -> Dict[str, Any]:
        """Build cross-source validated insights."""
        cross = insights.get("cross_source_insights", {})
        
        return {
            "validated_pain_points": cross.get("ai_validated_pain_points", []),
            "opportunities": cross.get("opportunities", []),
            "ad_angles": cross.get("ad_angle_suggestions", []),
            "recommendations": cross.get("strategic_recommendations", []),
            "confidence_themes": cross.get("high_confidence_themes", []),
        }
    
    def _build_ad_intelligence(
        self,
        ad_library_data: Dict[str, Any],
        competitor_ads: List[Dict[str, Any]],
        insights: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build ad intelligence section."""
        patterns = insights.get("ad_creative_patterns", {})
        
        return {
            "brand_ads": ad_library_data.get("ads", [])[:10],
            "competitor_ads": competitor_ads[:10],
            "patterns": {
                "frameworks": patterns.get("frameworks", {}),
                "hook_types": patterns.get("hook_types", {}),
                "emotions": patterns.get("emotions", {}),
                "avg_hook_strength": patterns.get("avg_hook_strength", 0),
                "avg_effectiveness": patterns.get("avg_effectiveness", 0),
            },
            "top_transcriptions": patterns.get("top_transcriptions", [])[:5],
        }
    
    def _build_computed(
        self,
        scraped_data: List[Dict[str, Any]],
        video_analyses: List[Dict[str, Any]],
        insights: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build computed/derived data."""
        
        # Top frameworks from video analyses
        framework_counts = defaultdict(int)
        for va in video_analyses:
            fw = va.get("framework")
            if fw:
                framework_counts[fw] += 1
        
        top_frameworks = sorted(
            framework_counts.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:5]
        
        # Language patterns (frequent phrases)
        language_patterns = insights.get("customer_language", [])[:10]
        
        # Proto-ICPs
        proto_icps = insights.get("proto_icp_recommendations", [])
        
        return {
            "top_frameworks": [f[0] for f in top_frameworks],
            "framework_counts": dict(framework_counts),
            "language_patterns": language_patterns,
            "icp_clusters": proto_icps[:5],
            "pain_points": insights.get("pain_points", [])[:10],
            "value_props": insights.get("value_props", [])[:10],
        }
    
    def _build_coverage_metrics(
        self,
        scraped_data: List[Dict[str, Any]],
        video_analyses: List[Dict[str, Any]],
        insights: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build data coverage metrics for tracking data quality."""
        
        # Count by source
        source_counts = defaultdict(int)
        for item in scraped_data:
            source = item.get("source_type", "unknown")
            source_counts[source] += 1
        
        # Track what data is available
        has_data = {
            "scraped_data": len(scraped_data) > 0,
            "video_analyses": len(video_analyses) > 0,
            "verbatim_quotes": len(insights.get("verbatim_quotes", [])) > 0,
            "pain_points": len(insights.get("pain_points", [])) > 0,
            "icps": len(insights.get("icps", [])) > 0,
            "proto_icps": len(insights.get("proto_icp_recommendations", [])) > 0,
            "ad_patterns": bool(insights.get("ad_creative_patterns")),
        }
        
        coverage_pct = sum(has_data.values()) / len(has_data) * 100
        
        return {
            "by_source": dict(source_counts),
            "total_scraped": len(scraped_data),
            "video_count": len(video_analyses),
            "data_available": has_data,
            "coverage_percent": round(coverage_pct, 1),
        }


# Convenience function for quick access
def build_unified_data(
    brand: Dict[str, Any],
    scraped_data: List[Dict[str, Any]] = None,
    insights: Dict[str, Any] = None,
    video_analyses: List[Dict[str, Any]] = None,
    ad_library_data: Dict[str, Any] = None,
    competitor_ads: List[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Convenience function to build unified data."""
    return UnifiedDataLayer().build(
        brand=brand,
        scraped_data=scraped_data,
        insights=insights,
        video_analyses=video_analyses,
        ad_library_data=ad_library_data,
        competitor_ads=competitor_ads,
    )
