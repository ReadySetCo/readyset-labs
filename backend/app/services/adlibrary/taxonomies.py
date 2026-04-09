# -*- coding: utf-8 -*-
"""
Creative Taxonomies for Video Ad Analysis.
Based on IMA v46 taxonomy - comprehensive creative dimensions.
"""

TAXONOMY_VERSION = "v1-2024-12-22"

# =============================================================================
# CORE TAXONOMIES
# =============================================================================

TONE = [
    "Empathetic",
    "Emotional",
    "Educational",
    "Encouraging",
    "Fun",
    "Imperative",
    "Authoritative",
    "Casual",
    "Aspirational",
    "Urgent",
    "Comedic",
    "Relatable",
    "Inspirational",
]

VISUAL_TYPE = [
    "UGC → LOFI",
    "UGC → HIFI",
    "Organic/meme",
    "Elevated → cinematic, studio, premium",
    "Animated → motion design, stylized visuals",
    "Static",
    "AI generated",
]

NARRATION_DRIVER = [
    "Talking to Camera",
    "VO",
    "Text",
    "Trend Sound",
    "Video",
    "Music",
]

# NFC — Narrative Footage Categories (máx 2)
NFC = [
    "After",
    "After - Talent",
    "Before",
    "Before - Talent",
    "Competitor",
    "Competitor - Talent",
    "Delivery",
    "Delivery - Talent",
    "Hero",
    "Nitro",
    "Nitro - Talent",
    "Screen",
    "Screen - Talent",
    "Showing",
    "Showing - Talent",
    "Talking",
    "Unboxing",
    "Unboxing - Talent",
    "Using",
    "Using - Talent",
    "Supportive",
    "Disruptive",
]

OPENER_VISUAL = list(NFC)

CREATIVE_FORMAT = [
    "Video Explainer (Educational Demo)",
    "Multi-Voice Testimonial Montage",
    "First-Person Testimonial",
    "Listicle",
    "POV (first-person)",
    "Get ready with me (GRWM)",
    "Montage (rapid visual sequence)",
    "Rhythm-Driven Video (Text-on-Beat)",
    "Street Interview (Man-on-the-Street)",
    "Walkthrough",
    "Reacting to",
    "A day in the life",
    "Brand Pitch",
    "Listening thoughts",
    "Long text",
]

PRODUCT_DISPLAY = [
    "Single Product",
    "Multi Product",
    "No Product Shown",
]

LENGTH = [
    "Short",
    "Medium",
    "LongForm",
]

FUNNEL_STAGE = [
    "TOFU",
    "MOFU",
    "BOFU",
    "NONE",
]

# =============================================================================
# FRAMEWORK & NARRATIVE
# =============================================================================

FRAMEWORK = [
    "Problem-Solution",
    "Reasons Why",
    "Listicle",
    "Get Ready With Me (GRWM)",
    "POV",
    "Walkthrough",
    "Before and After",
    "Reacting to",
    "A day in the life",
    "Street Interview",
    "Stitch Incoming",
    "Mythbusting",
    "Self Convo Skit",
    "Rating and Ranking",
    "Testimonial",
    "Unboxing",
    "Product Demo",
    "Storytelling",
    "Challenge",
    "Comparison",
    "How-To",
    "FAQ",
    "Trend Hijack",
    "Duet/Reply",
    "Green Screen Commentary",
    "Text Story",
    "Voiceover Narrative",
    "Interview",
    "Behind the Scenes",
    "Transformation",
]

EMOTION = [
    "Fear",
    "Hope",
    "Frustration",
    "Aspiration",
    "Relief",
    "Curiosity",
    "Belonging",
    "Pride",
    "Urgency",
    "Joy",
    "Trust",
    "Empowerment",
    "Nostalgia",
    "Excitement",
    "FOMO",
    "Confidence",
    "Comfort",
    "Validation",
]

# =============================================================================
# TALENT & SETTING
# =============================================================================

TALENT_TYPE = [
    "Real Customer",
    "Actor",
    "Influencer",
    "Expert",
    "Founder",
    "Employee",
    "Celebrity",
    "UGC Creator",
    "Model",
    "Spokesperson",
    "None",
]

TALENT_COUNT = [
    "Single",
    "Duo",
    "Multiple",
    "None",
]

SETTING_TYPE = [
    "Home",
    "Outdoor",
    "Studio",
    "Office",
    "Gym",
    "Store",
    "Bathroom",
    "Kitchen",
    "Bedroom",
    "Car",
    "Street",
    "Nature",
    "Restaurant",
    "Medical/Clinical",
    "Abstract/Virtual",
    "Mixed",
]

# =============================================================================
# VISUAL & AUDIO ELEMENTS
# =============================================================================

END_CARD = [
    "Branded",
    "Native",
    "None",
]

PACING = [
    "Slow",
    "Medium",
    "Fast",
]

MUSIC_ENERGY = [
    "Upbeat",
    "Calm",
    "Dramatic",
    "Trending",
    "Emotional",
    "Energetic",
    "Lo-Fi",
    "Cinematic",
    "Acoustic",
    "Electronic",
    "Hip-Hop",
    "None",
]

TEXT_STYLE = [
    "TikTok Native",
    "Instagram Native",
    "Branded",
    "Animated",
    "Karaoke/Sync",
    "Minimal",
    "Heavy",
    "None",
]

VISUAL_ELEMENT = [
    "Green Screen",
    "Split Screen",
    "Picture in Picture",
    "UI Mockup",
    "Product Closeup",
    "Text Overlay Heavy",
    "Emoji/Stickers",
    "Progress Bar",
    "Price Tag",
    "Countdown Timer",
    "Review Stars",
    "Chat Bubbles",
    "Search Bar",
    "Notification",
    "Transition Effect",
    "None",
]

AUDIO_MIX = [
    "VO Only",
    "Music Only",
    "VO + Music",
    "Dialogue",
    "Sound Effects Only",
    "Trending Sound",
    "Original Sound",
    "ASMR",
    "Silence",
    "Mix (VO + Music + SFX)",
    "Voiceover + Sound Effects",
    "Dialogue + Music",
]

# =============================================================================
# PROOF & URGENCY
# =============================================================================

PROOF_TYPE = [
    "Testimonial",
    "Statistics",
    "Before After",
    "Expert Endorsement",
    "Social Proof",
    "User Reviews",
    "Guarantee",
    "Clinical Study",
    "Awards",
    "Media Mention",
    "Certification",
    "Case Study",
    "None",
]

URGENCY_ELEMENT = [
    "Limited Time",
    "Scarcity",
    "FOMO",
    "Seasonal",
    "Flash Sale",
    "Countdown",
    "Exclusive Access",
    "Early Bird",
    "Last Chance",
    "None",
]

# =============================================================================
# HOOK & CTA
# =============================================================================

HOOK_TYPE = [
    "Question",
    "Statement",
    "Statistic",
    "Testimonial Quote",
    "Problem Statement",
    "Solution Statement",
    "Benefit Statement",
    "Fear/Warning",
    "How-To",
    "Listicle Number",
    "Challenge",
    "POV Statement",
    "None",
]

FIRST_FRAME_ELEMENT = [
    "Face",
    "Text",
    "Product",
    "Action",
    "Question",
    "Shocking Visual",
    "Logo",
    "Hands",
    "Before State",
    "Result/After",
    "UI/Screen",
    "Nature/Lifestyle",
]

CTA_PLACEMENT = [
    "End",
    "Middle",
    "Throughout",
    "Start",
    "None",
]

CTA_TYPE = [
    "Button",
    "Text",
    "Verbal",
    "Animated",
    "Swipe Up",
    "Link in Bio",
    "None",
]

# =============================================================================
# OFFER & INTENT
# =============================================================================

OFFER_TYPE = [
    "None",
    "% Discount",
    "$ Discount",
    "Free Trial",
    "Free Gift / Bonus",
    "Bundle / Pack",
    "Limited-Time Offer",
    "Other",
]

AD_INTENT = [
    "Awareness",
    "Consideration",
    "Conversion",
    "Retargeting",
    "Retention",
    "Brand Building",
    "Product Launch",
    "Promotion/Sale",
    "Education",
    "Lead Generation",
]

PROBLEM_SOLUTION_FLOW = [
    "Problem First",
    "Solution First",
    "Interleaved",
    "Solution Only",
    "Problem Only",
]

SCRIPT_POV = [
    "First-person",
    "Second-person",
    "Third-person",
    "Mixed",
]

SOUND_OFF_FRIENDLY = [
    "Yes",
    "Partial",
    "No",
]

SEASON = [
    "Evergreen",
    "Spring",
    "Summer",
    "Fall",
    "Winter",
    "New Year",
    "Valentine's Day",
    "Mother's Day",
    "Father's Day",
    "Back to School",
    "Halloween",
    "Thanksgiving",
    "Black Friday",
    "Cyber Monday",
    "Christmas",
    "Holiday Season",
    "Flash Sale",
    "Limited Time Offer",
    "Launch",
]

# =============================================================================
# REGISTRY - All taxonomies in one dict
# =============================================================================

TAXONOMIES = {
    # Core
    "tone": TONE,
    "visual_type": VISUAL_TYPE,
    "narration_driver": NARRATION_DRIVER,
    "nfc": NFC,
    "opener_visual": OPENER_VISUAL,
    "creative_format": CREATIVE_FORMAT,
    "product_display": PRODUCT_DISPLAY,
    "length": LENGTH,
    "funnel_stage": FUNNEL_STAGE,
    # Framework & Narrative
    "framework": FRAMEWORK,
    "emotion": EMOTION,
    # Talent & Setting
    "talent_type": TALENT_TYPE,
    "talent_count": TALENT_COUNT,
    "setting_type": SETTING_TYPE,
    # Visual & Audio
    "end_card": END_CARD,
    "pacing": PACING,
    "music_energy": MUSIC_ENERGY,
    "text_style": TEXT_STYLE,
    "visual_element": VISUAL_ELEMENT,
    "audio_mix": AUDIO_MIX,
    # Proof & Urgency
    "proof_type": PROOF_TYPE,
    "urgency_element": URGENCY_ELEMENT,
    # Hook & CTA
    "hook_type": HOOK_TYPE,
    "first_frame_element": FIRST_FRAME_ELEMENT,
    "cta_placement": CTA_PLACEMENT,
    "cta_type": CTA_TYPE,
    # Offer & Intent
    "offer_type": OFFER_TYPE,
    "ad_intent": AD_INTENT,
    "problem_solution_flow": PROBLEM_SOLUTION_FLOW,
    "script_pov": SCRIPT_POV,
    "sound_off_friendly": SOUND_OFF_FRIENDLY,
    "season": SEASON,
}


def get_taxonomy(name: str) -> list[str]:
    """Get canonical taxonomy list by name."""
    return TAXONOMIES.get(name.lower(), []).copy()
