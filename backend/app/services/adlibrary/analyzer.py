"""
Ad Analyzer - Analyzes ads using Gemini Vision API.
Extracts creative dimensions based on IMA v46 taxonomy.
Enhanced with 30+ creative dimension fields.
"""

import os
import json
import re
import time
import asyncio
import subprocess
from typing import Dict, Any, List, Optional
from pathlib import Path

import google.generativeai as genai

from ...config import settings
from .taxonomies import TAXONOMIES, get_taxonomy


class AdAnalyzer:
    """Analyzes ad creatives using Gemini Vision API."""
    
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        if self.api_key:
            genai.configure(api_key=self.api_key)
        self.model_id = "models/gemini-3-flash-preview"
        # Base directory for resolving relative paths
        self.base_dir = Path(__file__).parent.parent.parent.parent  # backend/
    
    def _resolve_media_path(self, media_path: str) -> str:
        """Resolve media path to absolute path."""
        if not media_path:
            return media_path
        
        path = Path(media_path)
        
        # If already absolute and exists, return as-is
        if path.is_absolute() and path.exists():
            return str(path)
        
        # Try relative to base_dir (backend/)
        resolved = self.base_dir / media_path
        if resolved.exists():
            return str(resolved)
        
        # Try relative to current working directory
        cwd_resolved = Path.cwd() / media_path
        if cwd_resolved.exists():
            return str(cwd_resolved)
        
        # Return original path (will fail with clear error message)
        return media_path
        
    def _get_video_duration(self, path: str) -> Optional[float]:
        """Get video duration using ffprobe."""
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return float(result.stdout.strip())
        except (FileNotFoundError, subprocess.TimeoutExpired, ValueError, OSError) as e:
            print(f"    [!] Could not get video duration: {e}")
            return None

    def _build_analysis_prompt(self) -> str:
        """Build the IMA-style analysis prompt with 30+ creative dimensions."""
        return f"""You are an expert video ad analyst with deep knowledge of creative strategy, 
performance marketing, and social media advertising. Analyze the video thoroughly and extract 
structured data into a JSON object.

## OUTPUT FORMAT RULES
- Multiple tags: Use || separator (e.g., "ValueA||ValueB")
- Single tag: Just the value (no brackets)
- Empty field: Use "" (empty string, never "N/A" or "null")
- Numbers: Use actual numbers, not strings

## TRANSCRIPTION (CRITICAL)
"transcription": Provide a VERBATIM transcription of ALL spoken words in the video.
- Transcribe exactly what is said, word for word
- Include any on-screen text that is read aloud
- If there is no speech, write "No speech"

## HOOK & OPENING (First 3 seconds)
- "opening_copy": Exact text/speech shown in first 3 seconds (transcribe literally)
- "hook_type": One of {TAXONOMIES.get('hook_type', [])}
- "hook_strength_1to5": 1-5 rating. USE FULL RANGE:
  * 1 = Very weak, unlikely to stop scroll
  * 2 = Below average, might not grab attention
  * 3 = Average, decent but not memorable
  * 4 = Strong, likely to stop scroll
  * 5 = Exceptional, very strong scroll-stopper
- "first_frame_element": One of {TAXONOMIES.get('first_frame_element', [])}
- "opener_visual_description": Brief description of what's happening visually in first 3 seconds

## FRAMEWORK & NARRATIVE STRUCTURE
- "framework": One of {TAXONOMIES.get('framework', [])}
  * "Problem-Solution": Opens with problem, presents product as solution
  * "Testimonial": Customer sharing experience
  * "Before and After": Shows transformation
  * "POV": First-person perspective
  * "Get Ready With Me (GRWM)": Talent preparing while discussing product
- "problem_solution_flow": One of {TAXONOMIES.get('problem_solution_flow', [])}
- "script_pov": One of {TAXONOMIES.get('script_pov', [])}
- "creative_format": One of {TAXONOMIES.get('creative_format', [])}
- "funnel_stage": One of {TAXONOMIES.get('funnel_stage', [])}
- "ad_intent": One of {TAXONOMIES.get('ad_intent', [])}

## EMOTION & TONE
- "emotion": One of {TAXONOMIES.get('emotion', [])}
  * Fear, Hope, Frustration, FOMO, Trust, Relief, Curiosity, etc.
- "tone": One of {TAXONOMIES.get('tone', [])}
  * Empathetic, Educational, Comedic, Urgent, Aspirational, etc.

## VISUAL & AUDIO ELEMENTS
- "visual_type": One of {TAXONOMIES.get('visual_type', [])}
- "pacing": One of {TAXONOMIES.get('pacing', [])} (Slow/Medium/Fast)
- "music_energy": One of {TAXONOMIES.get('music_energy', [])}
- "audio_mix": One of {TAXONOMIES.get('audio_mix', [])}
- "text_style": One of {TAXONOMIES.get('text_style', [])}
- "visual_element": One of {TAXONOMIES.get('visual_element', [])} (use || for multiple)
- "narration_driver": One of {TAXONOMIES.get('narration_driver', [])}
- "nfc": One of {TAXONOMIES.get('nfc', [])} (Narrative Footage Category, max 2 with ||)
- "sound_off_friendly": One of {TAXONOMIES.get('sound_off_friendly', [])}

## TALENT & SETTING
- "talent_type": One of {TAXONOMIES.get('talent_type', [])}
- "talent_count": One of {TAXONOMIES.get('talent_count', [])}
- "setting_type": One of {TAXONOMIES.get('setting_type', [])}
- "product_display": One of {TAXONOMIES.get('product_display', [])}
- "end_card": One of {TAXONOMIES.get('end_card', [])}

## CTA (Call-to-Action)
- "cta_all": All CTAs shown (transcribe verbatim)
- "cta_placement": One of {TAXONOMIES.get('cta_placement', [])}
- "cta_type": One of {TAXONOMIES.get('cta_type', [])}
- "cta_destination": Where CTA leads (App, Website, App Store, Landing Page)

## PROOF & URGENCY
- "proof_type": One of {TAXONOMIES.get('proof_type', [])}
- "urgency_element": One of {TAXONOMIES.get('urgency_element', [])}
- "season": One of {TAXONOMIES.get('season', [])} (use "Evergreen" if not time-specific)

## OFFER
- "offer_type": One of {TAXONOMIES.get('offer_type', [])}
- "offer_intensity_1to5": 1-5 rating (1=soft mention, 5=very aggressive)
- "discount_code": Exact code if shown, else ""

## TIMING (in seconds)
- "brand_intro_second": When brand first appears (-1 if never, 0 if immediate)
- "product_intro_second": When product first appears (-1 if never)
- "duration_seconds": Total video length
- "scene_count": Number of distinct scenes/cuts

## STRATEGIC ANALYSIS (longer text - be detailed)
- "angle_label": 8-10 word human-readable description of the ad's angle/approach
  Example: "Anxious Professional | Problem-Solution | Easy Online Prescription"
- "awareness_level": One of "Unaware", "Problem Aware", "Solution Aware", "Product Aware", "Most Aware"
  * Unaware: ad educates about a problem the viewer doesn't know they have
  * Problem Aware: ad names a known pain and agitates it — no product yet
  * Solution Aware: ad positions product as the answer to a known need
  * Product Aware: ad differentiates from competitors or handles objections
  * Most Aware: ad leads with offer, urgency, or social proof for ready buyers
- "primary_psychological_trigger": The dominant cognitive bias the ad leverages (e.g., "Loss Aversion", "Social Signaling", "Zeigarnik Effect", "Zero-Risk Bias", "Authority Bias", "Scarcity/FOMO", "Anchoring", "Reciprocity")
- "high_fidelity_description": Detailed description of entire ad - what happens start to finish
- "strategic_summary": Why this ad works, what makes it effective, key takeaways (3-5 sentences)
- "transferable_principles": Array of 3-5 principles. Each follows the format: "This works because [mechanism]. Future briefs should [specific action]." These convert ad analysis into brief directions.
- "iteration_suggestions": {{
    "alternative_hooks": ["3 hooks for the same angle but different opening moves"],
    "format_variations": ["Same angle in different formats (UGC, static, founder ad, etc.)"],
    "fatigue_signals": ["Metrics that indicate this ad is dying: rising frequency, dropping CTR, etc."]
  }}
- "key_claims": Main claims or promises made
- "target_audience_inferred": Who this ad seems to target
- "effectiveness_score_1to5": Overall effectiveness rating

## FULL TEXT SUMMARY (CRITICAL - for database ingestion)
- "ad_summary": A comprehensive 200-400 word text description of this video ad that captures EVERYTHING important for reference. Write it as a detailed narrative that includes: the opening hook and how it grabs attention, the complete transcription integrated naturally, the visual style and production quality, the emotional journey, the offer/CTA, and strategic analysis of why the ad works. This text should be detailed enough that someone reading it can understand the complete ad without watching the video. Include specific quotes from the transcription. Start with "This video ad opens with..." and be thorough.

## SCENE BREAKDOWN (STRUCTURED ARRAY - CRITICAL FOR VIDEO ADS)
- "scene_breakdown": Array of scene objects. For EACH distinct scene/segment in the video, include:
  [
    {{
      "scene_number": 1,
      "timestamp_start": "00:00",
      "timestamp_end": "00:03",
      "duration_seconds": 3,
      "scene_type": "Hook",
      "visual_description": "Close-up of frustrated person looking at phone",
      "audio_transcript": "Are you tired of...",
      "on_screen_text": "TIRED OF THIS?"
    }},
    ...
  ]
  * scene_type options: Hook, Problem, Solution, Testimonial, Product Demo, CTA, Transition, Before, After, Social Proof
  * Include ALL scenes from start to end of video
  * If no speech in scene, use "" for audio_transcript
  * If no text overlay, use "" for on_screen_text

## CREATIVE DIMENSIONS (IMA Style - Critical for Script Generation)
- "target_persona": Primary audience persona (e.g., "Busy Professional Mom", "Health-Conscious Millennial")
- "pain_points": List of specific problems addressed, use || separator (e.g., "time constraints||expensive alternatives||lack of results")
- "value_props": List of benefits/solutions offered, use || separator (e.g., "saves time||affordable||proven results")
- "messaging_angle": Core persuasive angle (e.g., "Convenience without compromise", "Premium results at budget price")
- "core_insights": Key human truths or psychological insights leveraged (e.g., "People want quick wins", "Fear of missing out on trends")
- "product_category": Category of product/service (e.g., "Skincare", "SaaS", "Food & Beverage")
- "concept": One-line concept summary (e.g., "Before/after transformation showing product efficacy")

## FREE TEXT INSIGHTS (1-3 sentences each)
- "core_insight_text": The human truth or psychological insight the ad leverages
- "pain_points_text": Specific problems, frustrations, or challenges shown/addressed
- "value_props_text": Concrete benefits, solutions, or value the product offers
- "messaging_angle_text": The central claim, promise, or persuasive angle

## BRAND VISUAL IDENTITY
- "dominant_colors": List of 3-5 hex color codes (e.g., ["#ff5500", "#1a1a1a"])
- "visual_aesthetic_keywords": 3-5 keywords describing visual style

Return ONLY the JSON object, no markdown or explanation.
Analyze THIS video independently. Base selections on what you SEE and HEAR, not assumptions."""

    async def analyze_video(self, video_path: str) -> Optional[Dict[str, Any]]:
        """
        Analyze a video ad using Gemini Vision.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Dict with all extracted dimensions
        """
        from datetime import datetime
        
        if not self.api_key:
            print("    [!] Gemini API key not configured")
            return None
            
        if not os.path.exists(video_path):
            print(f"    [!] Video file not found: {video_path}")
            return None
        
        # Logging: Start time and file info
        start_time = datetime.now()
        file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
        video_name = os.path.basename(video_path)
        
        print(f"    [GEMINI VIDEO] Starting analysis: {video_name}")
        print(f"       File: {file_size_mb:.2f} MB")
        
        try:
            # Upload video to Gemini
            print(f"       -> Uploading to Gemini...")
            upload_start = datetime.now()
            video_file = genai.upload_file(video_path, mime_type="video/mp4")
            
            # Wait for processing with timeout (max 2 minutes)
            wait_time = 0
            max_wait = 120
            while video_file.state.name == "PROCESSING":
                if wait_time >= max_wait:
                    print(f"    [!] Video processing timeout after {max_wait}s")
                    return None
                time.sleep(2)
                wait_time += 2
                video_file = genai.get_file(video_file.name)
            
            if video_file.state.name != "ACTIVE":
                print(f"    [!] Video processing failed: {video_file.state.name}")
                return None
            
            upload_time = (datetime.now() - upload_start).total_seconds()
            print(f"       Upload + processing: {upload_time:.1f}s")
            
            # Get duration
            duration = self._get_video_duration(video_path)
            print(f"       Video duration: {duration:.1f}s")
            
            # Analyze with Gemini (with timeout)
            print(f"       -> Analyzing with Gemini Vision...")
            analysis_start = datetime.now()
            model = genai.GenerativeModel(self.model_id)
            prompt = self._build_analysis_prompt()
            
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(model.generate_content, [prompt, video_file]),
                    timeout=90.0  # 90 seconds for video analysis
                )
            except asyncio.TimeoutError:
                print(f"    [!] Gemini timeout after 90s for video analysis")
                return None
            
            analysis_time = (datetime.now() - analysis_start).total_seconds()
            
            # Parse response
            result = self._extract_json(response.text)
            
            if result:
                # Normalize field names to match frontend expectations
                result = self._normalize_analysis_response(result)
                result["duration_seconds"] = duration
                result["media_type"] = "video"
                result["analysis_source"] = "gemini"
            
            # Clean up uploaded file
            try:
                genai.delete_file(video_file.name)
            except Exception as e:
                print(f"    [!] Failed to delete uploaded video file: {e}")

            # Logging: Final stats
            total_time = (datetime.now() - start_time).total_seconds()
            # Cost estimate: ~$0.00025/sec for video input + ~$0.01/1K output tokens
            estimated_cost = (duration * 0.00025) + 0.02  # rough estimate
            
            print(f"    [GEMINI VIDEO] Complete: {video_name}")
            print(f"       Analysis time: {analysis_time:.1f}s | Total: {total_time:.1f}s")
            print(f"       Est. cost: ${estimated_cost:.3f}")
            
            return result
            
        except Exception as e:
            print(f"    [!] Video analysis error: {e}")
            return None
    
    async def analyze_image(self, image_path: str, ad_copy: str = None) -> Optional[Dict[str, Any]]:
        """
        Analyze a static image ad using Gemini Vision.
        
        Args:
            image_path: Path to the image file
            ad_copy: Optional ad copy text to include in analysis
            
        Returns:
            Dict with extracted dimensions
        """
        from datetime import datetime
        
        if not self.api_key:
            print("    [!] Gemini API key not configured")
            return None
            
        if not os.path.exists(image_path):
            print(f"    [!] Image file not found: {image_path}")
            return None
        
        # Logging
        start_time = datetime.now()
        file_size_kb = os.path.getsize(image_path) / 1024
        image_name = os.path.basename(image_path)
        print(f"    [GEMINI IMAGE] {image_name} ({file_size_kb:.1f} KB)")
        
        try:
            # Upload image
            print(f"       -> Uploading to Gemini...")
            image_file = genai.upload_file(image_path)
            
            # Build prompt for static image — deep analysis aligned with video prompt
            prompt = f"""You are an expert ad analyst. Analyze this static ad image and extract structured data into a JSON object.

{f'Ad Copy Text: "{ad_copy}"' if ad_copy else 'No ad copy provided.'}

## OUTPUT FORMAT RULES
- Multiple tags: Use || separator (e.g., "ValueA||ValueB")
- Single tag: Just the value (no brackets)
- Empty field: Use "" (empty string, never "N/A" or "null")
- Numbers: Use actual numbers, not strings

## TRANSCRIPTION (CRITICAL)
- "transcription": Transcribe ALL visible text in the image — headlines, subheadlines, body copy, fine print, button labels, overlay text. Include everything verbatim. If no text, write "No text".

## HOOK & ATTENTION
- "hook": What is the hook/attention-grabber in this ad?
- "hook_type": One of {TAXONOMIES.get('hook_type', [])}
- "hook_strength_1to5": 1-5 rating (use full range: 1=weak, 3=average, 5=exceptional scroll-stopper)
- "first_frame_element": One of {TAXONOMIES.get('first_frame_element', [])}
- "headline": Main headline text visible (if any)

## FRAMEWORK & NARRATIVE STRUCTURE
- "framework": One of {TAXONOMIES.get('framework', [])}
- "problem_solution_flow": One of {TAXONOMIES.get('problem_solution_flow', [])}
- "creative_format": One of {TAXONOMIES.get('creative_format', [])}
- "funnel_stage": One of {TAXONOMIES.get('funnel_stage', [])}
- "ad_intent": One of {TAXONOMIES.get('ad_intent', [])}

## EMOTION & TONE
- "emotion": One of {TAXONOMIES.get('emotion', [])}
- "tone": One of {TAXONOMIES.get('tone', [])}

## VISUAL ELEMENTS
- "visual_type": One of {TAXONOMIES.get('visual_type', [])}
- "text_style": One of {TAXONOMIES.get('text_style', [])}
- "visual_element": One of {TAXONOMIES.get('visual_element', [])} (use || for multiple)
- "nfc": One of {TAXONOMIES.get('nfc', [])} (Narrative Footage Category, max 2 with ||)
- "color_scheme": Dominant colors and their effect
- "sound_off_friendly": One of {TAXONOMIES.get('sound_off_friendly', [])}

## TALENT & SETTING
- "talent_type": One of {TAXONOMIES.get('talent_type', [])}
- "talent_count": One of {TAXONOMIES.get('talent_count', [])}
- "setting_type": One of {TAXONOMIES.get('setting_type', [])}
- "product_display": One of {TAXONOMIES.get('product_display', [])}
- "end_card": One of {TAXONOMIES.get('end_card', [])}
- "brand_visible": Is brand logo clearly visible? ("Yes" / "No")
- "product_visible": Is the product shown? ("Yes" / "No")

## CTA (Call-to-Action)
- "cta_all": All visible CTAs (transcribe verbatim)
- "cta_placement": One of {TAXONOMIES.get('cta_placement', [])}
- "cta_type": One of {TAXONOMIES.get('cta_type', [])}

## PROOF & URGENCY
- "proof_type": One of {TAXONOMIES.get('proof_type', [])}
- "urgency_element": One of {TAXONOMIES.get('urgency_element', [])}
- "season": One of {TAXONOMIES.get('season', [])} (use "Evergreen" if not time-specific)

## OFFER
- "offer_type": One of {TAXONOMIES.get('offer_type', [])}
- "offer_intensity_1to5": 1-5 rating (1=soft mention, 5=very aggressive)
- "discount_code": Exact code if shown, else ""

## COPY ANALYSIS (from provided ad copy text)
- "copy_hook": Opening hook from the copy (first 10-15 words)
- "copy_cta": Call-to-action from the copy
- "copy_tone": Tone of the written copy
- "value_proposition": Main value proposition communicated

## STRATEGIC ANALYSIS (longer text — be detailed)
- "angle_label": 8-10 word description of the ad's angle/approach
- "high_fidelity_description": Detailed description of the entire ad — every visual element, text, layout, colors
- "strategic_summary": Why this ad works, what makes it effective, key takeaways (3-5 sentences)
- "key_claims": Main claims or promises made
- "target_audience_inferred": Who this ad seems to target
- "effectiveness_score_1to5": Overall effectiveness rating (1-5, use full range)

## SCENE BREAKDOWN (single scene for static)
- "scene_count": 1
- "scene_breakdown": Array with exactly ONE object:
  [{{
    "scene_number": 1,
    "timestamp_start": "static",
    "timestamp_end": "static",
    "duration_seconds": 0,
    "scene_type": "Full Creative",
    "visual_description": "Describe the full visual layout, composition, and key elements",
    "audio_transcript": "",
    "on_screen_text": "All visible text in the image"
  }}]

## FULL TEXT SUMMARY (CRITICAL — for database ingestion)
- "ad_summary": A comprehensive 200-400 word text description of this ad that captures EVERYTHING important. Write it as a detailed narrative that includes: the visual style and composition, headline and hook, all text content, the offer/CTA, the emotional appeal, the target audience, the messaging strategy, and why it might be effective or not. This text should be detailed enough that someone reading it can understand the complete ad without seeing the image. Start with "This static ad..." and be thorough and specific.

Return ONLY the JSON object, no markdown or explanation."""

            model = genai.GenerativeModel(self.model_id)
            
            # Add timeout to prevent hanging
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(model.generate_content, [prompt, image_file]),
                    timeout=75.0
                )
            except asyncio.TimeoutError:
                print(f"    [!] Gemini timeout after 75s for image analysis")
                return None
            
            result = self._extract_json(response.text)
            
            if result:
                # Normalize field names to match frontend expectations
                result = self._normalize_analysis_response(result)
                result["media_type"] = "image"
                result["analysis_source"] = "gemini"
            
            # Clean up
            try:
                genai.delete_file(image_file.name)
            except Exception as e:
                print(f"    [!] Failed to delete uploaded image file: {e}")

            return result
            
        except Exception as e:
            print(f"    [!] Image analysis error: {e}")
            return None
    
    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from response text."""
        if not text:
            return None
        try:
            # Try direct parse
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                return json.loads(match.group(0))
        except (json.JSONDecodeError, ValueError) as e:
            print(f"    [!] JSON direct parse failed: {e}")
        try:
            # Try cleaning markdown
            clean = text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"    [!] JSON markdown-cleaned parse failed: {e}")
        return None
    
    def _normalize_analysis_response(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize Gemini response fields to match frontend expectations.
        Maps field names and ensures correct data structures.
        """
        if not result:
            return result
        
        # Map hook_strength_1to5 -> hook_strength (frontend expects this name)
        if "hook_strength_1to5" in result and "hook_strength" not in result:
            result["hook_strength"] = result["hook_strength_1to5"]
        
        # Map effectiveness_score_1to5 -> effectiveness (frontend expects this name)
        if "effectiveness_score_1to5" in result and "effectiveness" not in result:
            result["effectiveness"] = result["effectiveness_score_1to5"]
        
        # Map offer_intensity_1to5 -> offer_intensity
        if "offer_intensity_1to5" in result and "offer_intensity" not in result:
            result["offer_intensity"] = result["offer_intensity_1to5"]
        
        # Ensure scene_breakdown is an array
        scene_breakdown = result.get("scene_breakdown")
        if scene_breakdown:
            if isinstance(scene_breakdown, str):
                # If it's a string, wrap it in an array with a single scene object
                result["scene_breakdown"] = [{
                    "scene_number": 1,
                    "scene_type": "Full Video",
                    "visual_description": scene_breakdown,
                    "audio_transcript": "",
                    "on_screen_text": ""
                }]
            elif not isinstance(scene_breakdown, list):
                # If it's neither string nor list, reset to empty
                result["scene_breakdown"] = []
        else:
            # If scene_breakdown doesn't exist but scene_by_scene_breakdown does, convert it
            legacy_breakdown = result.get("scene_by_scene_breakdown")
            if legacy_breakdown and isinstance(legacy_breakdown, str):
                result["scene_breakdown"] = [{
                    "scene_number": 1,
                    "scene_type": "Full Video",
                    "visual_description": legacy_breakdown,
                    "audio_transcript": "",
                    "on_screen_text": ""
                }]
        
        return result
    
    async def analyze_ad_text_only(self, ad: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Analyze an ad using only its text/metadata when no media file is available.
        
        Args:
            ad: Ad dict with ad_copy, cta, etc.
            
        Returns:
            Dict with extracted dimensions
        """
        if not self.api_key:
            return None
            
        ad_copy = ad.get("ad_copy", "")
        cta = ad.get("cta", "")
        discount = ad.get("discount_code", "")
        
        if not ad_copy and not cta:
            return None
        
        try:
            media_type = ad.get("media_type", "image")
            ad_format = "static image/graphic" if media_type != "video" else "video"
            
            prompt = f"""You are an expert ad creative analyst. Analyze this Facebook {ad_format} ad based on its text copy and metadata. Produce a COMPLETE creative analysis as if you had reviewed the full creative.

AD COPY:
{ad_copy or 'No copy available'}

CTA BUTTON: {cta or 'Unknown'}
DISCOUNT CODE: {discount or 'None'}
PLATFORMS: {', '.join(ad.get('platforms', ['Facebook']))}
AD FORMAT: {(ad.get('display_format') or media_type or 'Static Image').upper()}

Return a JSON object with ALL of these fields:

BASIC DIMENSIONS:
- "tone": Detected tone (Empathetic, Educational, Comedic, Urgent, Aspirational, Direct, Conversational)
- "emotion": Primary emotion evoked (Fear, Hope, FOMO, Trust, Relief, Curiosity, Excitement, Pride)
- "framework": Ad framework (Problem-Solution, Testimonial, Before-After, Direct Response, Listicle, Brand Awareness, Product Demo, How-To, Challenge, Social Proof)
- "hook_type": Type of hook (Question, Statistic, Pain Point, Benefit Statement, Solution Statement, Bold Claim, Empathy Statement)
- "hook_strength_1to5": 1-5 rating (1=weak, 5=exceptional scroll-stopper)
- "offer_type": Offer type if any (Discount, Free Trial, Bundle, Free Shipping, BOGO, None)
- "urgency_element": Urgency elements if any (Limited Time, Low Stock, Countdown, Seasonal, None)
- "cta_all": The call-to-action text verbatim
- "proof_type": Type of proof (Social Proof, Statistics, Testimonial, Before-After, None, Certifications)
- "target_audience_inferred": Specific audience persona this targets
- "pain_points_text": Specific problems/frustrations addressed in the copy
- "value_props_text": Key benefits and solutions offered
- "messaging_angle_text": The central persuasive angle/claim
- "effectiveness_score_1to5": Overall ad effectiveness 1-5

STRATEGIC FIELDS:
- "angle_label": 6-10 word human-readable description of the ad's angle (e.g. "Acne Sufferer | Problem-Solution | Dermatologist-Backed Solution")
- "high_fidelity_description": Detailed description of what this ad communicates — layout, hierarchy, imagery inferred from copy, messaging flow (2-4 sentences)
- "strategic_summary": Why this ad works strategically, key creative decisions, target insights (2-3 sentences)
- "funnel_stage": One of (Awareness, Consideration, Conversion, Retention)
- "creative_format": One of (Single Image, Carousel, Video, Collection, Story)
- "product_category": The product/service category
- "target_persona": Primary audience persona (e.g. "Acne-Prone Teen", "Busy Working Mom")

FULL TEXT SUMMARY (CRITICAL):
- "ad_summary": A comprehensive 150-250 word description of this ad that captures everything important. Describe: what the headline/hook is, what problem it addresses, what solution/product it promotes, the offer if any, the CTA, and WHY this creative approach is effective. Write in present tense as if describing the ad to someone who hasn't seen it. Start with "This static ad features..." or "This ad uses..."

SCENE BREAKDOWN (treat as a single static frame):
- "scene_breakdown": Array with exactly ONE object representing the full static creative:
  [{{
    "scene_number": 1,
    "timestamp_start": "static",
    "timestamp_end": "static",
    "duration_seconds": 0,
    "scene_type": "Full Creative",
    "visual_description": "Inferred visual layout based on copy: describe what the image likely shows, text hierarchy, product placement, color feel",
    "audio_transcript": "",
    "on_screen_text": "{ad_copy[:200] if ad_copy else ''}"
  }}]

- "opening_copy": The first sentence or headline from the ad copy
- "visual_type": Inferred visual type (Product Shot, Lifestyle, Graphic Design, Before-After, Text-Heavy)
- "sound_off_friendly": "Yes" (static ads are always sound-off friendly)
- "media_type": "static_image"

Return ONLY the JSON object. No markdown, no explanation."""

            model = genai.GenerativeModel(self.model_id)
            
            response = await asyncio.wait_for(
                asyncio.to_thread(model.generate_content, prompt),
                timeout=30.0
            )
            
            result = self._extract_json(response.text)
            
            if result:
                # Normalize field names to match frontend expectations
                result = self._normalize_analysis_response(result)
                result["media_type"] = "text_only"
                result["analysis_source"] = "gemini_text"
                
            return result
            
        except Exception as e:
            print(f"    [!] Text-only analysis error: {e}")
            return None
    
    async def analyze_ads_batch(
        self, 
        ads: List[Dict[str, Any]],
        max_videos: int = 20,
        max_images: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Analyze a batch of ads.
        
        Args:
            ads: List of ad dicts with media_file paths
            max_videos: Max videos to analyze
            max_images: Max images to analyze
            
        Returns:
            List of ads with analysis added
        """
        analyzed = []
        video_count = 0
        image_count = 0
        text_count = 0
        max_text = 25  # Limit text-only analyses (increased from 10 to cover static ads)
        total_ads = len(ads)
        
        print(f"    [Gemini] Starting analysis of {total_ads} ads...")
        
        for i, ad in enumerate(ads, 1):
            ad_id = ad.get('library_id', 'unknown')
            media_path = ad.get("media_file")
            analysis = None

            # Determine media type early so we know what to do when media_file is missing
            is_video = ad.get("has_video", False) or ad.get("media_type") == "video"
            if media_path:
                # Refine based on actual file extension
                is_video = is_video or media_path.endswith(('.mp4', '.webm', '.mkv'))

            if media_path:
                # Resolve relative paths to absolute
                media_path = self._resolve_media_path(media_path)

                if is_video and video_count < max_videos:
                    print(f"    [{i}/{total_ads}] Analyzing VIDEO ad {ad_id}...")
                    analysis = await self.analyze_video(media_path)
                    video_count += 1
                    if analysis:
                        hook = analysis.get('hook', {}).get('text', 'N/A')[:50]
                        framework = analysis.get('framework', 'N/A')
                        print(f"           -> Hook: \"{hook}...\"")
                        print(f"           -> Framework: {framework}")
                elif not is_video and image_count < max_images:
                    print(f"    [{i}/{total_ads}] Analyzing IMAGE ad {ad_id}...")
                    analysis = await self.analyze_image(media_path, ad.get("ad_copy"))
                    image_count += 1
                    if analysis:
                        framework = analysis.get('framework', 'N/A')
                        print(f"           -> Framework: {framework}")

            # For static ads without a local file: download on-the-fly and analyze
            # This ensures statics get full Gemini vision analysis, not just text-only
            if not analysis and not is_video and image_count < max_images:
                image_url = ad.get("image_url") or ad.get("thumbnail_url")
                if image_url and not image_url.startswith("/api/"):
                    print(f"    [{i}/{total_ads}] Downloading image on-the-fly for ad {ad_id}...")
                    try:
                        import httpx as _httpx
                        from pathlib import Path as _Path
                        import tempfile as _tempfile
                        async with _httpx.AsyncClient(timeout=20.0, follow_redirects=True) as _client:
                            _resp = await _client.get(image_url, headers={"User-Agent": "Mozilla/5.0"})
                            if _resp.status_code == 200 and len(_resp.content) > 1000:
                                with _tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as _tmp:
                                    _tmp.write(_resp.content)
                                    _tmp_path = _tmp.name
                                analysis = await self.analyze_image(_tmp_path, ad.get("ad_copy"))
                                try:
                                    _Path(_tmp_path).unlink(missing_ok=True)
                                except Exception:
                                    pass
                                if analysis:
                                    image_count += 1
                                    analysis["media_type"] = "image"
                                    framework = analysis.get('framework', 'N/A')
                                    print(f"           -> Framework: {framework}")
                            else:
                                print(f"           -> Image fetch failed (status={_resp.status_code})")
                    except Exception as _e:
                        print(f"           -> Image on-the-fly error: {str(_e)[:60]}")

            # Final fallback: text-only analysis (only when no image available at all)
            if not analysis and text_count < max_text and (ad.get("ad_copy") or ad.get("cta")):
                print(f"    [{i}/{total_ads}] TEXT-ONLY analysis for ad {ad_id}...")
                analysis = await self.analyze_ad_text_only(ad)
                if analysis:
                    text_count += 1
                    framework = analysis.get('framework', 'N/A')
                    print(f"           -> Framework: {framework}")
            
            if analysis:
                ad["creative_analysis"] = analysis
            else:
                print(f"    [{i}/{total_ads}] SKIPPED ad {ad_id} (no analysis possible)")
            
            analyzed.append(ad)
            
            # Rate limiting (async to avoid blocking the event loop)
            await asyncio.sleep(1)
        
        print(f"    [Gemini] Analysis complete: {video_count} videos, {image_count} images, {text_count} text-only")
        return analyzed
    
    def aggregate_patterns(self, analyzed_ads: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregate patterns across analyzed ads.
        
        Args:
            analyzed_ads: List of ads with creative_analysis
            
        Returns:
            Dict with aggregated patterns and insights
        """
        frameworks = []
        hooks = []
        hook_strengths = []
        tones = []
        emotions = []
        cta_placements = []
        offer_types = []
        proof_types = []
        transcriptions = []
        effectiveness_scores = []
        
        for ad in analyzed_ads:
            analysis = ad.get("creative_analysis", {})
            if not analysis:
                continue
            
            if analysis.get("framework"):
                frameworks.append(analysis["framework"])
            if analysis.get("hook_type"):
                hooks.append(analysis["hook_type"])
            if analysis.get("hook_strength_1to5"):
                hook_strengths.append(analysis["hook_strength_1to5"])
            if analysis.get("tone"):
                tones.append(analysis["tone"])
            if analysis.get("emotion"):
                emotions.append(analysis["emotion"])
            if analysis.get("cta_placement"):
                cta_placements.append(analysis["cta_placement"])
            if analysis.get("offer_type"):
                offer_types.append(analysis["offer_type"])
            if analysis.get("proof_type"):
                proof_types.append(analysis["proof_type"])
            if analysis.get("transcription"):
                transcriptions.append({
                    "library_id": ad.get("library_id"),
                    "text": analysis["transcription"],
                    "hook_strength": analysis.get("hook_strength_1to5"),
                    "effectiveness": analysis.get("effectiveness_score_1to5")
                })
            if analysis.get("effectiveness_score_1to5"):
                effectiveness_scores.append(analysis["effectiveness_score_1to5"])
        
        def count_items(items: List) -> Dict[str, int]:
            """Count items with case normalization to avoid duplicate keys."""
            counts = {}
            # Track canonical names (first occurrence)
            canonical = {}
            for item in items:
                if not item:
                    continue
                # Normalize to title case for comparison
                normalized = str(item).strip().title()
                if normalized not in canonical:
                    canonical[normalized] = str(item).strip()
                key = canonical[normalized]
                counts[key] = counts.get(key, 0) + 1
            return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))
        
        def safe_avg(items: List) -> float:
            """Calculate average with safe type conversion."""
            numeric_items = []
            for item in items:
                try:
                    numeric_items.append(float(item))
                except (ValueError, TypeError):
                    pass
            return sum(numeric_items) / len(numeric_items) if numeric_items else 0
        
        return {
            "total_analyzed": len([a for a in analyzed_ads if a.get("creative_analysis")]),
            "frameworks": count_items(frameworks),
            "hook_types": count_items(hooks),
            "avg_hook_strength": safe_avg(hook_strengths),
            "tones": count_items(tones),
            "emotions": count_items(emotions),
            "cta_placements": count_items(cta_placements),
            "offer_types": count_items(offer_types),
            "proof_types": count_items(proof_types),
            "avg_effectiveness": safe_avg(effectiveness_scores),
            "top_transcriptions": sorted(
                transcriptions, 
                key=lambda x: float(x.get("effectiveness") or 0) if isinstance(x.get("effectiveness"), (int, float, str)) else 0, 
                reverse=True
            )[:5]
        }




