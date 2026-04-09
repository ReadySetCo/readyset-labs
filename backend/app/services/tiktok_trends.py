# -*- coding: utf-8 -*-
"""
TikTok Trends Service - Surfaces trending content patterns for creative strategy.

Extracts:
- Trending sounds/music in the niche
- Trending hashtags and their velocity
- Viral content patterns (hooks, formats, pacing)
- Engagement benchmarks for the category
"""

from typing import Dict, Any, List, Optional
from collections import Counter
from datetime import datetime
import re


class TikTokTrendsService:
    """Analyzes TikTok scraped data to surface trends and patterns."""
    
    def __init__(self):
        self.min_videos_for_trends = 5  # Minimum videos needed for trend analysis
    
    def analyze_trends(
        self,
        tiktok_data: List[Dict[str, Any]],
        brand_name: str = "",
        niche: str = ""
    ) -> Dict[str, Any]:
        """
        Analyze TikTok data to extract trending patterns.
        
        Args:
            tiktok_data: List of scraped TikTok videos
            brand_name: Brand name for context
            niche: Industry/niche for context
            
        Returns:
            Dict with trending sounds, hashtags, and patterns
        """
        if not tiktok_data or len(tiktok_data) < self.min_videos_for_trends:
            return {
                "status": "insufficient_data",
                "videos_analyzed": len(tiktok_data) if tiktok_data else 0,
                "trending_sounds": [],
                "trending_hashtags": [],
                "content_patterns": {},
                "engagement_benchmarks": {}
            }
        
        print(f"       [TikTok Trends] Analyzing {len(tiktok_data)} videos for trends...")
        
        # Extract and analyze different trend dimensions
        trending_sounds = self._extract_trending_sounds(tiktok_data)
        trending_hashtags = self._extract_trending_hashtags(tiktok_data)
        content_patterns = self._analyze_content_patterns(tiktok_data)
        engagement_benchmarks = self._calculate_engagement_benchmarks(tiktok_data)
        viral_indicators = self._identify_viral_indicators(tiktok_data)
        
        result = {
            "status": "success",
            "videos_analyzed": len(tiktok_data),
            "analysis_timestamp": datetime.now().isoformat(),
            "niche": niche or "general",
            
            # Trending sounds with usage counts
            "trending_sounds": trending_sounds[:20],
            
            # Trending hashtags with velocity scores
            "trending_hashtags": trending_hashtags[:30],
            
            # Content patterns (formats, durations, styles)
            "content_patterns": content_patterns,
            
            # Engagement benchmarks for the niche
            "engagement_benchmarks": engagement_benchmarks,
            
            # Indicators of what makes content go viral in this niche
            "viral_indicators": viral_indicators,
            
            # Actionable recommendations
            "recommendations": self._generate_recommendations(
                trending_sounds, trending_hashtags, content_patterns, viral_indicators
            )
        }
        
        print(f"       [TikTok Trends] Found {len(trending_sounds)} sounds, {len(trending_hashtags)} hashtags")
        return result
    
    def _extract_trending_sounds(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract and rank trending sounds/music from TikTok data."""
        sounds = []
        sound_counts = Counter()
        sound_engagement = {}
        
        for video in data:
            raw_data = video.get("raw_data", {})
            
            # Try multiple fields where sound info might be stored
            sound_name = None
            sound_author = None
            sound_id = None
            
            # From musicMeta (most common)
            music_meta = raw_data.get("musicMeta", {})
            if isinstance(music_meta, dict):
                sound_name = music_meta.get("musicName") or music_meta.get("title")
                sound_author = music_meta.get("musicAuthor") or music_meta.get("authorName")
                sound_id = music_meta.get("musicId") or music_meta.get("id")
            
            # From music field
            if not sound_name:
                music = raw_data.get("music", {})
                if isinstance(music, dict):
                    sound_name = music.get("title") or music.get("name")
                    sound_author = music.get("author") or music.get("authorName")
                    sound_id = music.get("id")
            
            # From direct fields
            if not sound_name:
                sound_name = raw_data.get("musicTitle") or raw_data.get("soundName")
                sound_author = raw_data.get("musicAuthor")
            
            if sound_name and sound_name.strip():
                clean_name = sound_name.strip()
                sound_counts[clean_name] += 1
                
                # Track engagement per sound
                engagement = video.get("likes", 0) + video.get("comments_count", 0) + video.get("shares", 0)
                if clean_name not in sound_engagement:
                    sound_engagement[clean_name] = {
                        "total_engagement": 0,
                        "video_count": 0,
                        "author": sound_author,
                        "sound_id": sound_id
                    }
                sound_engagement[clean_name]["total_engagement"] += engagement
                sound_engagement[clean_name]["video_count"] += 1
        
        # Build ranked list
        for sound_name, count in sound_counts.most_common(30):
            sound_info = sound_engagement.get(sound_name, {})
            avg_engagement = sound_info.get("total_engagement", 0) / max(sound_info.get("video_count", 1), 1)
            
            sounds.append({
                "name": sound_name,
                "author": sound_info.get("author", "Unknown"),
                "usage_count": count,
                "avg_engagement": round(avg_engagement),
                "trend_score": round(count * (avg_engagement / 1000 + 1), 2),  # Weighted score
                "sound_id": sound_info.get("sound_id")
            })
        
        # Sort by trend score
        sounds.sort(key=lambda x: x["trend_score"], reverse=True)
        return sounds
    
    def _extract_trending_hashtags(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract and rank trending hashtags from TikTok data."""
        hashtag_counts = Counter()
        hashtag_engagement = {}
        
        for video in data:
            raw_data = video.get("raw_data", {})
            
            # Get hashtags from multiple sources
            hashtags = []
            
            # From hashtags field
            if raw_data.get("hashtags"):
                hashtags.extend(raw_data["hashtags"])
            
            # From challenges field
            challenges = raw_data.get("challenges", [])
            for challenge in challenges:
                if isinstance(challenge, dict):
                    title = challenge.get("title") or challenge.get("name")
                    if title:
                        hashtags.append(title)
                elif isinstance(challenge, str):
                    hashtags.append(challenge)
            
            # Extract from text/description
            text = video.get("content", "") or raw_data.get("text", "") or raw_data.get("desc", "")
            if text:
                extracted = re.findall(r'#(\w+)', text)
                hashtags.extend(extracted)
            
            # Clean and count
            for tag in hashtags:
                if isinstance(tag, dict):
                    tag = tag.get("name") or tag.get("title", "")
                tag = str(tag).strip().lower().lstrip("#")
                if tag and len(tag) > 1:
                    hashtag_counts[tag] += 1
                    
                    engagement = video.get("likes", 0) + video.get("comments_count", 0)
                    if tag not in hashtag_engagement:
                        hashtag_engagement[tag] = {"total": 0, "count": 0}
                    hashtag_engagement[tag]["total"] += engagement
                    hashtag_engagement[tag]["count"] += 1
        
        # Build ranked list
        trending = []
        for tag, count in hashtag_counts.most_common(50):
            eng_data = hashtag_engagement.get(tag, {"total": 0, "count": 1})
            avg_eng = eng_data["total"] / max(eng_data["count"], 1)
            
            trending.append({
                "hashtag": f"#{tag}",
                "usage_count": count,
                "avg_engagement": round(avg_eng),
                "velocity_score": round(count * (1 + avg_eng / 10000), 2),
                "category": self._categorize_hashtag(tag)
            })
        
        trending.sort(key=lambda x: x["velocity_score"], reverse=True)
        return trending
    
    def _categorize_hashtag(self, tag: str) -> str:
        """Categorize a hashtag by type."""
        tag_lower = tag.lower()
        
        # Common TikTok hashtag patterns
        if any(x in tag_lower for x in ["fyp", "foryou", "viral", "trending", "blowup"]):
            return "discovery"
        if any(x in tag_lower for x in ["tutorial", "howto", "tips", "hack", "learn"]):
            return "educational"
        if any(x in tag_lower for x in ["review", "honest", "rating", "unboxing"]):
            return "review"
        if any(x in tag_lower for x in ["transformation", "before", "after", "glow", "results"]):
            return "transformation"
        if any(x in tag_lower for x in ["day", "life", "routine", "morning", "night"]):
            return "lifestyle"
        if any(x in tag_lower for x in ["funny", "comedy", "joke", "meme"]):
            return "entertainment"
        if any(x in tag_lower for x in ["duet", "stitch", "reply", "pov"]):
            return "format"
        
        return "niche"
    
    def _analyze_content_patterns(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze content patterns across videos."""
        durations = []
        formats = Counter()
        hook_styles = Counter()
        
        for video in data:
            raw_data = video.get("raw_data", {})
            
            # Duration analysis
            duration = 0
            if raw_data.get("videoMeta", {}).get("duration"):
                duration = raw_data["videoMeta"]["duration"]
            elif raw_data.get("duration"):
                duration = raw_data["duration"]
            elif raw_data.get("video", {}).get("duration"):
                duration = raw_data["video"]["duration"]
            
            if duration and duration > 0:
                durations.append(duration)
            
            # Detect format from text
            text = (video.get("content", "") or "").lower()
            if "pov:" in text or "pov " in text:
                formats["POV"] += 1
            if "storytime" in text or "story time" in text:
                formats["Storytime"] += 1
            if any(x in text for x in ["tutorial", "how to", "here's how"]):
                formats["Tutorial"] += 1
            if any(x in text for x in ["review", "honest opinion", "my experience"]):
                formats["Review"] += 1
            if "get ready with me" in text or "grwm" in text:
                formats["GRWM"] += 1
            if any(x in text for x in ["duet", "stitch"]):
                formats["Reaction"] += 1
            
            # Hook style detection (from first part of text)
            if text:
                first_words = text[:50].lower()
                if first_words.startswith(("wait", "stop", "hold on", "no way")):
                    hook_styles["Pattern Interrupt"] += 1
                elif "?" in first_words[:30]:
                    hook_styles["Question"] += 1
                elif any(first_words.startswith(x) for x in ["i found", "i discovered", "i tried"]):
                    hook_styles["Discovery"] += 1
                elif any(first_words.startswith(x) for x in ["this is", "here's", "the"]):
                    hook_styles["Statement"] += 1
                elif any(x in first_words for x in ["you need", "you have to", "don't"]):
                    hook_styles["Direct Address"] += 1
        
        # Calculate duration stats
        duration_stats = {}
        if durations:
            durations.sort()
            duration_stats = {
                "avg_seconds": round(sum(durations) / len(durations)),
                "median_seconds": durations[len(durations) // 2],
                "most_common_range": self._get_duration_range(durations),
                "distribution": {
                    "under_15s": len([d for d in durations if d < 15]),
                    "15_30s": len([d for d in durations if 15 <= d < 30]),
                    "30_60s": len([d for d in durations if 30 <= d < 60]),
                    "over_60s": len([d for d in durations if d >= 60])
                }
            }
        
        return {
            "duration_stats": duration_stats,
            "popular_formats": [{"format": f, "count": c} for f, c in formats.most_common(10)],
            "hook_styles": [{"style": s, "count": c} for s, c in hook_styles.most_common(10)]
        }
    
    def _get_duration_range(self, durations: List[int]) -> str:
        """Get the most common duration range."""
        ranges = {"under_15s": 0, "15_30s": 0, "30_60s": 0, "over_60s": 0}
        for d in durations:
            if d < 15:
                ranges["under_15s"] += 1
            elif d < 30:
                ranges["15_30s"] += 1
            elif d < 60:
                ranges["30_60s"] += 1
            else:
                ranges["over_60s"] += 1
        
        max_range = max(ranges, key=ranges.get)
        range_labels = {
            "under_15s": "Under 15 seconds",
            "15_30s": "15-30 seconds", 
            "30_60s": "30-60 seconds",
            "over_60s": "Over 60 seconds"
        }
        return range_labels.get(max_range, "Unknown")
    
    def _calculate_engagement_benchmarks(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate engagement benchmarks for the niche."""
        likes = [v.get("likes", 0) for v in data if v.get("likes")]
        comments = [v.get("comments_count", 0) for v in data if v.get("comments_count")]
        shares = [v.get("shares", 0) for v in data if v.get("shares")]
        
        def percentile(arr, p):
            if not arr:
                return 0
            arr_sorted = sorted(arr)
            k = (len(arr_sorted) - 1) * p / 100
            f = int(k)
            c = f + 1 if f + 1 < len(arr_sorted) else f
            return arr_sorted[f] + (arr_sorted[c] - arr_sorted[f]) * (k - f) if f != c else arr_sorted[f]
        
        return {
            "likes": {
                "avg": round(sum(likes) / len(likes)) if likes else 0,
                "median": round(percentile(likes, 50)),
                "top_10_percent": round(percentile(likes, 90)),
                "top_1_percent": round(percentile(likes, 99))
            },
            "comments": {
                "avg": round(sum(comments) / len(comments)) if comments else 0,
                "median": round(percentile(comments, 50)),
                "top_10_percent": round(percentile(comments, 90))
            },
            "shares": {
                "avg": round(sum(shares) / len(shares)) if shares else 0,
                "median": round(percentile(shares, 50)),
                "top_10_percent": round(percentile(shares, 90))
            },
            "engagement_rate_benchmark": {
                "good": "2-5%",
                "great": "5-10%",
                "viral": "10%+"
            }
        }
    
    def _identify_viral_indicators(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Identify what makes content go viral in this niche."""
        # Sort by engagement to identify top performers
        sorted_data = sorted(
            data, 
            key=lambda x: x.get("likes", 0) + x.get("comments_count", 0) * 5,  # Comments weighted higher
            reverse=True
        )
        
        top_10_percent = sorted_data[:max(1, len(sorted_data) // 10)]
        
        # Analyze what top performers have in common
        top_hashtags = Counter()
        top_sounds = Counter()
        top_formats = Counter()
        
        for video in top_10_percent:
            raw_data = video.get("raw_data", {})
            
            # Hashtags
            text = video.get("content", "") or ""
            hashtags = re.findall(r'#(\w+)', text)
            for tag in hashtags:
                top_hashtags[tag.lower()] += 1
            
            # Sounds
            music = raw_data.get("musicMeta", {})
            if isinstance(music, dict) and music.get("musicName"):
                top_sounds[music["musicName"]] += 1
        
        return {
            "sample_size": len(top_10_percent),
            "common_hashtags_in_viral": [
                {"hashtag": f"#{tag}", "frequency": count} 
                for tag, count in top_hashtags.most_common(10)
            ],
            "common_sounds_in_viral": [
                {"sound": sound, "frequency": count}
                for sound, count in top_sounds.most_common(5)
            ],
            "key_insight": self._generate_viral_insight(top_10_percent)
        }
    
    def _generate_viral_insight(self, top_videos: List[Dict]) -> str:
        """Generate a key insight about what drives virality."""
        if not top_videos:
            return "Insufficient data for viral analysis"
        
        # Analyze common patterns
        avg_length = 0
        question_hooks = 0
        
        for v in top_videos:
            text = v.get("content", "") or ""
            if "?" in text[:50]:
                question_hooks += 1
            
            duration = v.get("raw_data", {}).get("videoMeta", {}).get("duration", 0)
            if duration:
                avg_length += duration
        
        if top_videos:
            avg_length = avg_length / len(top_videos)
        
        insights = []
        if question_hooks > len(top_videos) * 0.4:
            insights.append("Question hooks perform well")
        if avg_length and avg_length < 30:
            insights.append("Short-form (under 30s) dominates")
        elif avg_length and avg_length > 45:
            insights.append("Longer storytelling content resonates")
        
        return "; ".join(insights) if insights else "Engagement varies - test different formats"
    
    def _generate_recommendations(
        self,
        sounds: List[Dict],
        hashtags: List[Dict],
        patterns: Dict,
        viral: Dict
    ) -> List[Dict[str, str]]:
        """Generate actionable recommendations based on trend analysis."""
        recommendations = []
        
        # Sound recommendation
        if sounds and sounds[0].get("usage_count", 0) >= 2:
            top_sound = sounds[0]
            recommendations.append({
                "type": "sound",
                "action": f"Use trending sound: '{top_sound['name']}'",
                "rationale": f"Used in {top_sound['usage_count']} videos with {top_sound['avg_engagement']} avg engagement"
            })
        
        # Hashtag strategy
        niche_tags = [h for h in hashtags if h.get("category") == "niche"][:3]
        discovery_tags = [h for h in hashtags if h.get("category") == "discovery"][:2]
        
        if niche_tags:
            recommendations.append({
                "type": "hashtags",
                "action": f"Include niche hashtags: {', '.join(h['hashtag'] for h in niche_tags)}",
                "rationale": "High relevance for target audience"
            })
        
        if discovery_tags:
            recommendations.append({
                "type": "hashtags", 
                "action": f"Add discovery hashtags: {', '.join(h['hashtag'] for h in discovery_tags)}",
                "rationale": "Increases reach beyond niche"
            })
        
        # Duration recommendation
        duration_stats = patterns.get("duration_stats", {})
        if duration_stats.get("most_common_range"):
            recommendations.append({
                "type": "format",
                "action": f"Target video length: {duration_stats['most_common_range']}",
                "rationale": f"Most common in this niche (median: {duration_stats.get('median_seconds', 'N/A')}s)"
            })
        
        # Hook recommendation
        hook_styles = patterns.get("hook_styles", [])
        if hook_styles:
            top_hook = hook_styles[0]
            recommendations.append({
                "type": "hook",
                "action": f"Use '{top_hook['style']}' hook style",
                "rationale": f"Most effective in analyzed content ({top_hook['count']} videos)"
            })
        
        # Viral insight
        if viral.get("key_insight"):
            recommendations.append({
                "type": "insight",
                "action": viral["key_insight"],
                "rationale": f"Based on top {viral.get('sample_size', 0)} performing videos"
            })
        
        return recommendations


# Singleton instance
_trends_service = None

def get_tiktok_trends_service() -> TikTokTrendsService:
    """Get TikTok trends service instance."""
    global _trends_service
    if _trends_service is None:
        _trends_service = TikTokTrendsService()
    return _trends_service
