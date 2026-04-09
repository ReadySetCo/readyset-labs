# -*- coding: utf-8 -*-
"""
TikTok Segment Analyzer - LLM-powered analysis of TikTok content for segment insights.

Provides two types of analysis:
1. Individual video analysis - Detailed breakdown of each video
2. Aggregated analysis - Patterns and insights across all videos

The data flows to: script generator, hooks library, RAG chat, dashboard.
"""

import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

import google.generativeai as genai

from ..config import settings


class TikTokSegmentAnalyzer:
    """
    Analyzes TikTok segment content using Gemini LLM.
    
    Extracts customer language, pain points, and content patterns for scriptwriting.
    """
    
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        if self.api_key:
            genai.configure(api_key=self.api_key)
        self.model_id = "models/gemini-3-flash-preview"
    
    def _build_individual_prompt(self, video_data: Dict[str, Any]) -> str:
        """
        Build prompt for individual video analysis.
        Focused on extracting actionable insights for scriptwriting.
        """
        content = video_data.get("content", "") or video_data.get("raw_data", {}).get("text", "")
        likes = video_data.get("likes", 0)
        comments = video_data.get("comments_count", 0)
        
        return f"""You are an expert TikTok content analyst specializing in understanding audience language and pain points.
Analyze this TikTok post/video for insights useful for creating advertising scripts.

POST DATA:
- Content/Caption: "{content[:2000] if content else 'No caption'}"
- Engagement: {likes} likes, {comments} comments
- Source: TikTok (segment research)

Return a JSON object with these fields:

## CUSTOMER LANGUAGE (Key for Copywriting)
- "verbatim_phrases": [List of exact phrases the audience uses - capture their real language]
- "slang_terms": [Any slang, abbreviations, or community-specific language]
- "emotional_words": [Words that convey emotion: frustrated, excited, obsessed, etc.]
- "tone": "Casual" | "Professional" | "Humorous" | "Frustrated" | "Excited" | "Skeptical"

## PAIN POINTS & DESIRES
- "pain_points": [Specific problems, frustrations, or challenges mentioned]
- "desires": [What they want, dream of, or aspire to]
- "objections": [Hesitations, concerns, or blockers mentioned]
- "questions_asked": [Questions they're asking - indicates information gaps]

## CONTENT PATTERNS
- "hook_text": First sentence or attention-grabber (first 10-15 words)
- "hook_type": "Question" | "Statement" | "Story" | "Controversy" | "Pain Point" | "Result" | "Tutorial"
- "format": "POV" | "Storytime" | "Tutorial" | "Review" | "GRWM" | "Day in Life" | "Before/After" | "Other"
- "cta_if_any": Call-to-action if present

## INSIGHTS FOR SCRIPTING
- "persuasion_angle": What persuasion angle is being used (social proof, authority, scarcity, etc.)
- "audience_segment": Who is this content for (demographics, psychographics in 15 words)
- "key_takeaway": One sentence summary of the main insight for ad creation

Return ONLY valid JSON. Be specific and extract actual quotes/phrases when possible."""
    
    def _build_aggregated_prompt(self, videos_summary: List[Dict[str, Any]], niche: str = "") -> str:
        """
        Build prompt for aggregated analysis across all videos.
        Synthesizes patterns for strategy-level insights.
        """
        # Create summary of individual analyses
        summaries = []
        for i, v in enumerate(videos_summary[:30], 1):  # Limit to 30 for token management
            summary = f"""
Video {i}:
- Tone: {v.get('tone', 'Unknown')}
- Pain points: {', '.join(v.get('pain_points', [])[:3])}
- Desires: {', '.join(v.get('desires', [])[:3])}
- Hook type: {v.get('hook_type', 'Unknown')}
- Format: {v.get('format', 'Unknown')}
- Key phrases: {', '.join(v.get('verbatim_phrases', [])[:3])}
"""
            summaries.append(summary)
        
        videos_text = "\n".join(summaries)
        
        return f"""You are a TikTok trends analyst synthesizing insights across multiple videos from the {niche or 'segment'} niche.

I've analyzed {len(videos_summary)} TikTok videos. Here are the individual summaries:

{videos_text}

Synthesize these into aggregated insights for ad creative strategy. Return a JSON object:

## AUDIENCE LANGUAGE PATTERNS
- "common_phrases": [Top 10 most repeated/common phrases across videos]
- "slang_dictionary": {{"term": "meaning"}} - Key slang and what it means
- "emotional_language": [Emotional words that resonate with this audience]
- "language_dos": [Language patterns TO USE in ads]
- "language_donts": [Language patterns to AVOID]

## PAIN POINTS RANKING
- "top_pain_points": [Top 5 most mentioned pain points, ranked by frequency]
- "underlying_fears": [Deeper fears behind the pain points]
- "unmet_needs": [Needs not being addressed by current solutions]

## DESIRES & ASPIRATIONS
- "top_desires": [Top 5 most mentioned desires, ranked by frequency]
- "transformation_they_want": One sentence describing the transformation they seek
- "identity_they_want": Who they want to become

## CONTENT STRATEGY INSIGHTS
- "best_hook_types": [Top 3 hook types that get engagement, with examples]
- "best_formats": [Top 3 content formats, with why they work]
- "optimal_tone": The tone that resonates most
- "engagement_drivers": [What makes content engaging in this niche]

## SCRIPT RECOMMENDATIONS
- "recommended_angles": [5 messaging angles to test based on patterns]
- "recommended_hooks": [5 hook examples based on what works]
- "proof_types_effective": [What types of proof this audience trusts]
- "objection_handling": [Common objections and how to address them]

## SEGMENT PROFILE SUMMARY
- "audience_persona": 50-word description of the typical audience member
- "core_motivation": Their primary motivation in 10 words
- "decision_factors": [Top 3 factors that drive their decisions]

Return ONLY valid JSON. Be specific and actionable for ad creation."""
    
    async def analyze_video(self, video_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Analyze a single TikTok video for audience insights.
        
        Args:
            video_data: Dict with content, likes, comments_count, raw_data
            
        Returns:
            Dict with extracted insights or None if analysis fails
        """
        if not self.api_key:
            return None
        
        try:
            prompt = self._build_individual_prompt(video_data)
            model = genai.GenerativeModel(self.model_id)
            
            response = await asyncio.wait_for(
                asyncio.to_thread(model.generate_content, prompt),
                timeout=30.0
            )
            
            result = self._extract_json(response.text)
            if result:
                result["analyzed_at"] = datetime.now().isoformat()
                result["source_type"] = "tiktok_segment"
            return result
            
        except asyncio.TimeoutError:
            print(f"       [TikTok Analyzer] Timeout analyzing video")
            return None
        except Exception as e:
            print(f"       [TikTok Analyzer] Error: {e}")
            return None
    
    async def analyze_batch(
        self, 
        videos: List[Dict[str, Any]],
        max_analyze: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Analyze a batch of TikTok videos individually.
        
        Args:
            videos: List of video dicts
            max_analyze: Maximum videos to analyze
            
        Returns:
            List of videos with analysis added
        """
        analyzed = []
        total = min(len(videos), max_analyze)
        
        print(f"       [TikTok Segment] Analyzing {total} videos individually...")
        
        for i, video in enumerate(videos[:max_analyze], 1):
            print(f"       [{i}/{total}] Analyzing TikTok post...")
            
            analysis = await self.analyze_video(video)
            if analysis:
                video["segment_analysis"] = analysis
                analyzed.append(video)
            
            # Rate limiting
            await asyncio.sleep(0.5)
        
        print(f"       [TikTok Segment] {len(analyzed)} videos analyzed")
        return analyzed
    
    async def aggregate_insights(
        self,
        analyzed_videos: List[Dict[str, Any]],
        niche: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        Synthesize aggregated insights from individually analyzed videos.
        
        Args:
            analyzed_videos: Videos with segment_analysis field
            niche: Niche/segment name for context
            
        Returns:
            Dict with aggregated insights
        """
        if not self.api_key or not analyzed_videos:
            return None
        
        # Extract individual analyses
        individual_analyses = []
        for v in analyzed_videos:
            analysis = v.get("segment_analysis", {})
            if analysis:
                individual_analyses.append(analysis)
        
        if len(individual_analyses) < 3:
            print(f"       [TikTok Segment] Not enough analyzed videos for aggregation ({len(individual_analyses)})")
            return None
        
        print(f"       [TikTok Segment] Aggregating insights from {len(individual_analyses)} videos...")
        
        try:
            prompt = self._build_aggregated_prompt(individual_analyses, niche)
            model = genai.GenerativeModel(self.model_id)
            
            response = await asyncio.wait_for(
                asyncio.to_thread(model.generate_content, prompt),
                timeout=60.0
            )
            
            result = self._extract_json(response.text)
            if result:
                result["analyzed_at"] = datetime.now().isoformat()
                result["videos_analyzed"] = len(individual_analyses)
                result["source"] = "tiktok_segment_aggregated"
            
            print(f"       [TikTok Segment] Aggregation complete")
            return result
            
        except asyncio.TimeoutError:
            print(f"       [TikTok Segment] Aggregation timeout")
            return None
        except Exception as e:
            print(f"       [TikTok Segment] Aggregation error: {e}")
            return None
    
    async def full_analysis(
        self,
        videos: List[Dict[str, Any]],
        niche: str = "",
        max_analyze: int = 20
    ) -> Dict[str, Any]:
        """
        Run full analysis: individual + aggregated.
        
        Args:
            videos: List of TikTok video dicts
            niche: Niche name
            max_analyze: Max videos to analyze
            
        Returns:
            Dict with individual_analyses and aggregated_insights
        """
        # Step 1: Individual analysis
        analyzed_videos = await self.analyze_batch(videos, max_analyze)
        
        # Step 2: Aggregated analysis
        aggregated = await self.aggregate_insights(analyzed_videos, niche)
        
        return {
            "individual_analyses": [v.get("segment_analysis") for v in analyzed_videos if v.get("segment_analysis")],
            "aggregated_insights": aggregated,
            "videos_processed": len(analyzed_videos),
            "analysis_timestamp": datetime.now().isoformat()
        }
    
    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from LLM response."""
        if not text:
            return None
        try:
            import re
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                return json.loads(match.group(0))
        except:
            pass
        try:
            clean = text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean)
        except:
            pass
        return None


# Singleton instance
_segment_analyzer = None


def get_tiktok_segment_analyzer() -> TikTokSegmentAnalyzer:
    """Get TikTok segment analyzer instance."""
    global _segment_analyzer
    if _segment_analyzer is None:
        _segment_analyzer = TikTokSegmentAnalyzer()
    return _segment_analyzer
