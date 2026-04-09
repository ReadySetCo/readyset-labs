"""
Social Media Analyzer - Downloads and analyzes TikTok/Instagram videos.
Uses yt-dlp for download and Gemini for analysis.
Similar to AdAnalyzer but for social media content.
"""

import os
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
import google.generativeai as genai

from ..config import settings


class SocialMediaAnalyzer:
    """
    Downloads and analyzes social media videos (TikTok, Instagram).
    Extracts transcriptions, hooks, and content insights.
    """
    
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        if self.api_key:
            genai.configure(api_key=self.api_key)
        self.model_id = "models/gemini-3-flash-preview"
        self.output_dir = Path("output/social_media")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    async def download_video(
        self, 
        video_url: str, 
        platform: str,
        video_id: str
    ) -> Optional[Path]:
        """
        Download a video using yt-dlp.
        
        Args:
            video_url: URL of the video
            platform: 'tiktok' or 'instagram'
            video_id: Unique identifier for the video
            
        Returns:
            Path to downloaded video file
        """
        platform_dir = self.output_dir / platform
        platform_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = platform_dir / f"{platform}_{video_id}.mp4"
        
        if output_path.exists():
            print(f"       [Download] Video already exists: {video_id}")
            return output_path
        
        try:
            print(f"       [Download] Downloading {platform} video: {video_id}...")
            result = subprocess.run([
                'yt-dlp',
                '-o', str(output_path),
                '--no-warnings',
                '-q',
                '--max-filesize', '50M',  # Limit file size
                video_url
            ], capture_output=True, text=True, timeout=60)
            
            if output_path.exists():
                print(f"       [Download] Success: {video_id}")
                return output_path
            
            # Check for other extensions
            for ext in ['.mp4', '.webm', '.mkv']:
                alt_path = platform_dir / f"{platform}_{video_id}{ext}"
                if alt_path.exists():
                    return alt_path
            
            print(f"       [Download] Failed: {video_id} (no file created)")
            return None
            
        except subprocess.TimeoutExpired:
            print(f"       [Download] Timeout: {video_id}")
            return None
        except Exception as e:
            print(f"       [Download] Error: {e}")
            return None
    
    async def analyze_video(
        self, 
        video_path: str,
        context: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze a social media video using Gemini.
        
        Args:
            video_path: Path to the video file
            context: Additional context (e.g., video description, hashtags)
            
        Returns:
            Dict with analysis results
        """
        if not self.api_key:
            print("       [Analyze] Gemini API key not configured")
            return None
            
        if not os.path.exists(video_path):
            print(f"       [Analyze] Video not found: {video_path}")
            return None
        
        try:
            print(f"       [Analyze] Uploading video to Gemini...")
            video_file = genai.upload_file(video_path, mime_type="video/mp4")
            
            # Wait for processing
            wait_time = 0
            max_wait = 60  # 1 minute max for social videos
            while video_file.state.name == "PROCESSING":
                if wait_time >= max_wait:
                    print(f"       [Analyze] Processing timeout")
                    return None
                await asyncio.sleep(2)
                wait_time += 2
                video_file = genai.get_file(video_file.name)
            
            if video_file.state.name != "ACTIVE":
                print(f"       [Analyze] Processing failed: {video_file.state.name}")
                return None
            
            prompt = self._build_analysis_prompt(context)
            
            print(f"       [Analyze] Analyzing with Gemini...")
            model = genai.GenerativeModel(self.model_id)
            
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(model.generate_content, [prompt, video_file]),
                    timeout=60.0
                )
            except asyncio.TimeoutError:
                print(f"       [Analyze] Gemini timeout")
                return None
            
            # Parse response
            result = self._extract_json(response.text)
            
            # Cleanup
            try:
                genai.delete_file(video_file.name)
            except:
                pass
            
            return result
            
        except Exception as e:
            print(f"       [Analyze] Error: {e}")
            return None
    
    def _build_analysis_prompt(self, context: str = "") -> str:
        """Build IMA-style analysis prompt for social media video analysis with 30+ dimensions."""
        return f"""You are an expert social media video analyst for TikTok and Instagram Reels.
Analyze this video comprehensively for advertising insights.

{f'CONTEXT (description/hashtags): {context}' if context else ''}

Return a JSON object with ALL of the following dimensions:

## 1. TRANSCRIPTION (VERBATIM)
- "transcription": Complete word-for-word transcription of ALL spoken words
- "key_message": Main takeaway in 1-2 sentences
- "quotable_phrases": [list of 3-5 memorable phrases for ads]

## 2. HOOK ANALYSIS (First 3 seconds are critical)
- "hook": Exact text/action in first 3 seconds
- "hook_type": "Question" | "Statement" | "Visual Shock" | "Curiosity Gap" | "Challenge" | "POV Statement" | "Call Out" | "Trend Reference" | "Problem Statement" | "Transformation Tease"
- "hook_strength": 1-5 (5 = scroll-stopping)
- "hook_technique": Brief explanation of why it works/doesn't work
- "first_frame_element": "Face" | "Text" | "Product" | "Action" | "Shocking Visual" | "Hands" | "Before State" | "Result"

## 3. VIRAL FORMAT DETECTION (IMPORTANT for TikTok/IG)
- "creative_format": Must be one of: "POV (first-person)" | "Get Ready With Me (GRWM)" | "Storytime" | "Duet/React" | "Stitch" | "Tutorial/How-To" | "Before/After Transformation" | "Day in the Life" | "Unboxing" | "Review" | "Comedy Skit" | "Trend Participation" | "Educational Explainer" | "Testimonial" | "Lifestyle" | "Behind the Scenes" | "Montage" | "Street Interview" | "Challenge" | "Other"
- "trend_detected": true/false
- "trend_name": Name of trend if applicable (e.g., "Get ready with me", "POV:", "#trend")

## 4. AUDIO & SOUND (Critical for TikTok)
- "audio_type": "Trending Sound" | "Original Audio" | "Voiceover" | "Music + Voiceover" | "Dialogue" | "ASMR" | "Sound Effects" | "Silence" | "Mix"
- "music_energy": "High" | "Medium" | "Low" | "No Music"
- "sound_name": If trending sound, the name or description of the sound
- "sound_viral_potential": 1-5 (how recognizable/viral is the sound)

## 5. CREATIVE DIMENSIONS
- "tone": "Casual" | "Professional" | "Humorous" | "Emotional" | "Urgent" | "Inspiring" | "Educational" | "Conversational" | "Provocative" | "FOMO"
- "pacing": "Fast" | "Medium" | "Slow" | "Variable"
- "visual_style": "Lo-fi UGC" | "Hi-fi UGC" | "Professional" | "Text-Heavy" | "B-Roll Heavy" | "Face-to-Camera" | "Screen Recording" | "Mixed"
- "production_quality": "Low-Budget" | "Medium" | "High-Quality" | "Native/Authentic"
- "setting": "Home" | "Outdoor" | "Studio" | "Car" | "Bathroom" | "Kitchen" | "Office" | "Public" | "Abstract"

## 6. TALENT ANALYSIS
- "talent_type": "Real Customer" | "Influencer" | "Brand Founder" | "Employee" | "Actor" | "UGC Creator" | "Expert" | "No Talent"
- "talent_count": "Single" | "Duo" | "Multiple" | "None"
- "talent_demographics": Estimated age range, gender if visible

## 7. SCENE BREAKDOWN (Max 10 scenes)
- "scene_breakdown": [
    {{
      "scene_number": 1,
      "timestamp_start": "0:00",
      "timestamp_end": "0:03",
      "duration_seconds": 3,
      "scene_type": "Hook" | "Problem" | "Solution" | "Benefit" | "Testimonial" | "CTA" | "Transition" | "Product Demo",
      "visual_description": "Brief description of what's shown",
      "audio_transcript": "What's said in this scene"
    }}
  ]

## 8. ADVERTISING INSIGHTS
- "pain_points_mentioned": [list of problems/frustrations expressed]
- "solutions_shown": [list of solutions/benefits demonstrated]
- "emotional_triggers": [list: "Relatability" | "FOMO" | "Aspiration" | "Fear" | "Curiosity" | "Trust" | "Urgency" | "Belonging"]
- "target_audience": Who this content is for (demographics, psychographics)
- "cta": Call-to-action used (if any)
- "cta_type": "Link in Bio" | "Comment" | "Follow" | "Save" | "Share" | "Shop Now" | "Learn More" | "None"

## 9. REPLICATION GUIDE (For Ad Creation)
- "effectiveness_score": 1-5 (how effective for ads)
- "why_it_works": Brief explanation of success factors
- "replication_difficulty": "Easy" | "Medium" | "Hard"
- "key_elements_to_replicate": [list of 3-5 elements to copy]
- "framework": "Problem-Solution" | "Before-After" | "Testimonial" | "How-To" | "Listicle" | "Story Arc" | "Direct Response" | "Trend-Based"

## 10. VISUAL BRANDING
- "dominant_colors": ["#hex1", "#hex2"] - 3-5 prominent colors
- "text_overlays_present": true/false
- "text_overlay_style": Description of font/color if present
- "visual_aesthetic": [list: "Modern" | "Minimalist" | "Bold" | "Earthy" | "Premium" | "Playful" | "Dark" | "Bright" | "Authentic"]

## 11. IMA CREATIVE DIMENSIONS (For Script Generation)
- "target_persona": Primary audience persona (e.g., "Busy Professional Mom", "Gen-Z Beauty Enthusiast")
- "pain_points": Structured list using || separator (e.g., "time constraints||expensive alternatives||lack of results")
- "value_props": Structured list using || separator (e.g., "saves time||affordable||proven results")
- "messaging_angle": Core persuasive angle (e.g., "Convenience without compromise")
- "core_insights": Key human truths leveraged
- "product_category": Category of product/service advertised
- "concept": One-line concept summary for replication

Return ONLY valid JSON. Be comprehensive and specific."""
    
    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from response text."""
        import json
        import re
        
        if not text:
            return None
        try:
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
    
    async def analyze_social_content(
        self,
        scraped_data: List[Dict[str, Any]],
        platform: str,
        max_videos: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Analyze a batch of social media content.
        Downloads videos and analyzes them with Gemini.
        
        Args:
            scraped_data: List of scraped posts from Apify
            platform: 'tiktok' or 'instagram'
            max_videos: Maximum videos to analyze
            
        Returns:
            List of posts with analysis added
        """
        analyzed = []
        video_count = 0
        
        print(f"    [{platform.upper()}] Analyzing {min(max_videos, len(scraped_data))} videos...")
        
        for item in scraped_data:
            # TikTok via Apify uses: webVideoUrl, mediaUrls
            # Instagram via Apify uses: displayUrl, videoUrl  
            # Standard format uses: source_url, video_url
            video_url = (
                item.get("source_url") or 
                item.get("video_url") or
                item.get("webVideoUrl") or  # TikTok via Apify
                (item.get("mediaUrls", [None])[0] if item.get("mediaUrls") else None) or  # TikTok fallback
                item.get("videoUrl") or  # Instagram video
                item.get("displayUrl")  # Instagram image/video
            )
            
            if not video_url or video_count >= max_videos:
                analyzed.append(item)
                continue
            
            # Generate unique ID
            video_id = str(hash(video_url))[-8:]
            
            # Download video
            video_path = await self.download_video(video_url, platform, video_id)
            
            if video_path:
                # Get context from scraped data (TikTok uses 'text', Instagram uses 'caption')
                context_parts = [
                    item.get('content', ''),
                    item.get('text', ''),  # TikTok via Apify
                    item.get('caption', ''),  # Instagram
                    item.get('title', ''),
                    ' '.join(item.get('hashtags', []) if isinstance(item.get('hashtags'), list) else [])
                ]
                context = ' '.join([p for p in context_parts if p]).strip()
                
                # Analyze with Gemini
                analysis = await self.analyze_video(str(video_path), context)
                
                if analysis:
                    item["video_analysis"] = analysis
                    item["video_file"] = str(video_path)
                    video_count += 1
                    print(f"       [+] Analyzed video {video_count}/{max_videos}")
            
            analyzed.append(item)
            
            # Rate limiting
            await asyncio.sleep(1)
        
        print(f"    [{platform.upper()}] Analyzed {video_count} videos")
        return analyzed
    
    async def aggregate_social_insights(
        self,
        analyzed_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Aggregate insights from analyzed social content with IMA-style dimensions.
        
        Args:
            analyzed_data: List of posts with video_analysis
            
        Returns:
            Aggregated insights with viral formats, sounds, hooks, and patterns
        """
        hooks = []
        pain_points = []
        quotable_phrases = []
        creative_formats = []
        transcriptions = []
        trending_sounds = []
        tones = []
        frameworks = []
        effectiveness_scores = []
        replication_guides = []
        scene_types = []
        
        for item in analyzed_data:
            analysis = item.get("video_analysis", {})
            if not analysis:
                continue
            
            # Hook analysis (enhanced)
            if analysis.get("hook"):
                hooks.append({
                    "hook": analysis["hook"],
                    "type": analysis.get("hook_type"),
                    "strength": analysis.get("hook_strength") or analysis.get("hook_strength_1to5", 0),
                    "technique": analysis.get("hook_technique"),
                    "first_frame": analysis.get("first_frame_element")
                })
            
            # Pain points & quotes
            if analysis.get("pain_points_mentioned"):
                if isinstance(analysis["pain_points_mentioned"], list):
                    pain_points.extend(analysis["pain_points_mentioned"])
            
            if analysis.get("quotable_phrases"):
                if isinstance(analysis["quotable_phrases"], list):
                    quotable_phrases.extend(analysis["quotable_phrases"])
            
            # Viral formats (NEW)
            if analysis.get("creative_format"):
                creative_formats.append({
                    "format": analysis["creative_format"],
                    "trend_detected": analysis.get("trend_detected", False),
                    "trend_name": analysis.get("trend_name")
                })
            
            # Trending sounds (NEW)
            if analysis.get("audio_type") == "Trending Sound" or analysis.get("sound_viral_potential", 0) >= 3:
                trending_sounds.append({
                    "sound_name": analysis.get("sound_name", "Unknown"),
                    "audio_type": analysis.get("audio_type"),
                    "music_energy": analysis.get("music_energy"),
                    "viral_potential": analysis.get("sound_viral_potential", 0)
                })
            
            # Tone & framework (NEW)
            if analysis.get("tone"):
                tones.append(analysis["tone"])
            if analysis.get("framework"):
                frameworks.append(analysis["framework"])
            
            # Effectiveness scores (NEW)
            if analysis.get("effectiveness_score"):
                effectiveness_scores.append(analysis["effectiveness_score"])
            
            # Replication guides (NEW)
            if analysis.get("key_elements_to_replicate"):
                replication_guides.append({
                    "elements": analysis["key_elements_to_replicate"],
                    "difficulty": analysis.get("replication_difficulty", "Medium"),
                    "why_it_works": analysis.get("why_it_works")
                })
            
            # Scene breakdown stats (NEW)
            if analysis.get("scene_breakdown"):
                for scene in analysis["scene_breakdown"]:
                    if scene.get("scene_type"):
                        scene_types.append(scene["scene_type"])
            
            # Transcriptions
            if analysis.get("transcription"):
                transcriptions.append({
                    "text": analysis["transcription"],
                    "source": item.get("source_url"),
                    "author": item.get("author"),
                    "effectiveness": analysis.get("effectiveness_score", 0)
                })
        
        # Calculate averages
        avg_effectiveness = sum(effectiveness_scores) / len(effectiveness_scores) if effectiveness_scores else 0
        avg_hook_strength = sum(h.get("strength", 0) for h in hooks) / len(hooks) if hooks else 0
        
        return {
            "total_analyzed": len([d for d in analyzed_data if d.get("video_analysis")]),
            "avg_effectiveness": round(avg_effectiveness, 1),
            "avg_hook_strength": round(avg_hook_strength, 1),
            
            # Hook intelligence
            "top_hooks": sorted(hooks, key=lambda x: x.get("strength", 0), reverse=True)[:5],
            "hook_types": self._count_items([h.get("type") for h in hooks]),
            
            # Viral formats & trends
            "viral_formats": self._count_items([f.get("format") for f in creative_formats]),
            "trends_detected": [f for f in creative_formats if f.get("trend_detected")][:5],
            
            # Sound intelligence
            "trending_sounds": sorted(trending_sounds, key=lambda x: x.get("viral_potential", 0), reverse=True)[:5],
            
            # Creative patterns
            "tones": self._count_items(tones),
            "frameworks": self._count_items(frameworks),
            "scene_types": self._count_items(scene_types),
            
            # Content for ads
            "pain_points": list(set(pain_points))[:10],
            "quotable_phrases": list(set(quotable_phrases))[:10],
            "transcriptions": sorted(transcriptions, key=lambda x: x.get("effectiveness", 0), reverse=True)[:5],
            
            # Replication playbook
            "replication_guides": replication_guides[:3]
        }
    
    def _count_items(self, items: List) -> Dict[str, int]:
        """Count occurrences of items."""
        counts = {}
        for item in items:
            if item:
                counts[item] = counts.get(item, 0) + 1
        return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))
