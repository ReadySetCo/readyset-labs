"""
Auto-populate "The Ready Set Way Database" Excel template from pipeline output.

Produces the xlsx shipped as the `rsw_database` export format.

Conventions for writing the template:
- Col A = field label (kept intact, acts as prompt/reference for the user).
- Col B = VALUE (where we write).
- Col C = Source metadata (brand_dna, ctp_builder, ad_library_analyzer, ...).
- Col D = Validation (left as-is — the template ships with `False` checkboxes in col E on some rows).
- Col E = Notes (derivation flag: direct / derived / global_agg).

Exception: "Angle 1..5" rows have a header `Angle | Hypothesis | Awareness | Validation | Notes`,
so the angle text goes in col A (replacing the prompt), Hypothesis in B, Awareness in C.

Sections we do NOT touch: Operational / Relationship / Media Buying.
"""
from __future__ import annotations

import io
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet


TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "rsw_database_template.xlsx"

# Map analyzer's 30 frameworks to the 16 the Excel template uses.
# Analyzer frameworks not in this map are ignored (GRWM, Duet/Reply, Green Screen, Self Convo Skit,
# Stitch Incoming, POV, Reacting to, Rating and Ranking, FAQ, Text Story, Voiceover Narrative,
# Behind the Scenes, Transformation, Challenge).
FRAMEWORK_NORMALIZE: Dict[str, str] = {
    "Problem-Solution": "Problem Solution",
    "Reasons Why": "Educational",
    "Listicle": "Listicle",
    "Walkthrough": "How To/ Tutorial",
    "Before and After": "Before/ After",
    "A day in the life": "Day in the Life",
    "Street Interview": "Street Interview",
    "Mythbusting": "Myth vs. Fact",
    "Testimonial": "Testimonials",
    "Unboxing": "Unboxing",
    "Product Demo": "How To/ Tutorial",
    "Storytelling": "Founder Story",
    "Comparison": "Comparison | Us vs. Them",
    "How-To": "How To/ Tutorial",
    "Trend Hijack": "Trend",
    "Interview": "Authority",
    "Educational": "Educational",
    "Offer/Promo": "Offer / Promo",
    "Objection Handling": "Objection Handling",
}

# The 16 frameworks in the Excel template (in order they appear in Strategy Layer).
EXCEL_FRAMEWORKS = [
    "Trend", "Educational", "Day in the Life", "Street Interview",
    "Problem Solution", "Myth vs. Fact", "Listicle", "Before/ After",
    "Comparison | Us vs. Them", "Authority", "How To/ Tutorial", "Founder Story",
    "Unboxing", "Objection Handling", "Testimonials", "Offer / Promo",
]


# =============================================================================
# Helpers
# =============================================================================

def _safe_str(value: Any, max_len: int = 32000) -> str:
    """Stringify a value safely for an Excel cell."""
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        parts = [_safe_str(v) for v in value if v]
        return "; ".join(p for p in parts if p)[:max_len]
    if isinstance(value, dict):
        # Pull the most useful key-ish field if present
        for key in ("hook", "quote", "name", "text", "value", "pain_point", "desire", "title", "barrier", "objection", "angle"):
            if key in value and value[key]:
                return str(value[key])[:max_len]
        return str(value)[:max_len]
    return str(value)[:max_len]


def _is_empty_or_gap(cell_value: Any) -> bool:
    """True if we can write to this cell without overwriting human content."""
    if cell_value is None:
        return True
    s = str(cell_value).strip()
    return s == "" or s == "GAP"


def _write(ws: Worksheet, row: int, col: int, value: Any, overwrite_non_gap: bool = False) -> bool:
    """Write only if the cell is empty or contains GAP. Returns True if we wrote."""
    if value is None or value == "":
        return False
    cur = ws.cell(row, col).value
    if not overwrite_non_gap and not _is_empty_or_gap(cur):
        return False
    ws.cell(row, col).value = _safe_str(value)
    return True


def _write_row_meta(
    ws: Worksheet,
    row: int,
    *,
    value: Optional[str] = None,
    source: Optional[str] = None,
    notes: Optional[str] = None,
    value_col: int = 2,  # col B
    source_col: int = 3,  # col C
    notes_col: int = 5,  # col E
) -> None:
    """Write value/source/notes to a standard field row."""
    if value is not None:
        _write(ws, row, value_col, value)
    if source is not None:
        _write(ws, row, source_col, source)
    if notes is not None:
        _write(ws, row, notes_col, notes)


def _find_row_starting_with(ws: Worksheet, col: int, prefix: str, start: int = 1, end: Optional[int] = None) -> Optional[int]:
    """Find the first row in `col` whose value starts with `prefix` (case-insensitive, trimmed).

    Handles multiline cells by checking the first line only — template cells
    often have prompt text after a newline that should not affect matching.
    """
    end = end or ws.max_row
    prefix_l = prefix.strip().lower()
    for r in range(start, end + 1):
        v = ws.cell(r, col).value
        if v is None:
            continue
        # Use first line only for matching (template cells have multiline prompts)
        first_line = str(v).split("\n")[0].strip().lower()
        if first_line.startswith(prefix_l):
            return r
    return None


def _find_ctp_anchors(ws: Worksheet) -> List[Tuple[int, int]]:
    """Return list of (ctp_number, starting_row) for each 'CTP N — ...' section header."""
    anchors = []
    for r in range(1, ws.max_row + 1):
        v = ws.cell(r, 1).value
        if v and isinstance(v, str):
            s = v.strip()
            import re as _re_anchor
            _m = _re_anchor.match(r"(?i)CTP\s+(\d+)\s*[—– \-‒]", s)
            if _m:
                anchors.append((int(_m.group(1)), r))
    # Dedup keeping first occurrence for each n
    seen = {}
    for n, r in anchors:
        if n not in seen:
            seen[n] = r
    return sorted(seen.items(), key=lambda kv: kv[0])


def _clone_ctp_block(ws, src_start: int, src_end: int, new_ctp_num: int) -> int:
    """Clone a CTP template block at the end of the sheet for a new CTP number.

    Copies column-A labels from *src_start..src_end-1*, rewrites
    'CTP <old_n>' references to 'CTP <new_n>', and returns the starting row.
    """
    import re as _re_clone, copy as _copy

    block_size = src_end - src_start
    insert_at = ws.max_row + 2  # blank spacer row

    first_val = ws.cell(src_start, 1).value or ""
    _m = _re_clone.match(r"(?i)CTP\s+(\d+)", first_val)
    old_n = int(_m.group(1)) if _m else 3

    for offset in range(block_size):
        src_row = src_start + offset
        dst_row = insert_at + offset
        for c in range(1, ws.max_column + 1):
            src_cell = ws.cell(src_row, c)
            dst_cell = ws.cell(dst_row, c)
            val = src_cell.value
            # Rewrite CTP number in col-A labels only
            if c == 1 and val and isinstance(val, str):
                val = _re_clone.sub(rf"CTP\s+{old_n}", f"CTP {new_ctp_num}", val)
                dst_cell.value = val
            # Copy formatting
            if src_cell.has_style:
                dst_cell.font = _copy.copy(src_cell.font)
                dst_cell.fill = _copy.copy(src_cell.fill)
                dst_cell.border = _copy.copy(src_cell.border)
                dst_cell.alignment = _copy.copy(src_cell.alignment)
                dst_cell.number_format = src_cell.number_format
    return insert_at


# =============================================================================
# Aggregations over ad_library_data
# =============================================================================

def _aggregate_creative_dims(ad_library_data: Any) -> Dict[str, List[Tuple[str, int]]]:
    """Aggregate top values for fields not already in insight.ad_creative_patterns."""
    ads: List[Dict[str, Any]] = []
    if isinstance(ad_library_data, dict):
        for key in ("ads", "brand_ads", "items", "results"):
            if isinstance(ad_library_data.get(key), list):
                ads = ad_library_data[key]
                break
    elif isinstance(ad_library_data, list):
        ads = ad_library_data

    counters: Dict[str, Counter] = {
        "framework": Counter(),
        "creative_format": Counter(),
        "visual_type": Counter(),
        "talent_type": Counter(),
        "first_frame_element": Counter(),
        "opener_visual_description": Counter(),
    }
    # Values that mean "no data" — filter these out so they don't pollute rankings
    _NULL_VALUES = {"None", "N/A", "n/a", "none", "Unknown", "unknown", ""}

    for ad in ads or []:
        if not isinstance(ad, dict):
            continue
        analysis = ad.get("creative_analysis") or {}
        if not isinstance(analysis, dict):
            continue
        for field in counters:
            val = analysis.get(field)
            if val and str(val).strip() not in _NULL_VALUES:
                counters[field][str(val).strip()] += 1

    return {k: c.most_common(10) for k, c in counters.items()}


def _top_frameworks_for_excel(framework_counts: List[Tuple[str, int]]) -> Dict[str, int]:
    """Normalize analyzer frameworks to Excel's 16 and keep counts. Unknown frameworks are dropped."""
    excel_counts: Dict[str, int] = {}
    for name, count in framework_counts:
        mapped = FRAMEWORK_NORMALIZE.get(name)
        if not mapped:
            # Case-insensitive fallback
            for k, v in FRAMEWORK_NORMALIZE.items():
                if k.lower() == name.lower():
                    mapped = v
                    break
        if mapped:
            excel_counts[mapped] = excel_counts.get(mapped, 0) + count
    return excel_counts


# =============================================================================
# Strategy Layer — Brand Information (rows ~3..17)
# =============================================================================

def _fill_brand_information(ws: Worksheet, brand: Any, insight: Any) -> None:
    """Fill the BRAND INFORMATION block at the top of Strategy Layer."""
    # Name
    r = _find_row_starting_with(ws, 1, "Brand Name", end=20)
    if r:
        _write_row_meta(ws, r, value=brand.name, source="brand_dna", notes="direct:brand.name")

    # Product / Service Name
    r = _find_row_starting_with(ws, 1, "Product/ Service Name", end=20) or _find_row_starting_with(ws, 1, "Product / Service Name", end=20)
    if r:
        products = brand.products or []
        product_name = ""
        if isinstance(products, list) and products:
            first = products[0]
            product_name = first if isinstance(first, str) else (first.get("name") if isinstance(first, dict) else "")
        _write_row_meta(ws, r, value=product_name, source="brand_dna", notes="direct:brand.products[0]")

    # Product / Service Description
    r = _find_row_starting_with(ws, 1, "Product/ Service Description", end=20) or _find_row_starting_with(ws, 1, "Product / Service Description", end=20)
    if r:
        _write_row_meta(ws, r, value=brand.description, source="brand_dna", notes="direct:brand.description")

    # Category
    r = _find_row_starting_with(ws, 1, "Category", end=20)
    if r:
        cat = " / ".join([x for x in [brand.sector, brand.vertical] if x])
        _write_row_meta(ws, r, value=cat, source="brand_dna", notes="direct:brand.sector+vertical")

    # Key Differentiators 1-5 from messaging_angles / competitor_analysis
    differentiators: List[str] = []
    ca = getattr(insight, "competitor_analysis", None) if insight else None
    if isinstance(ca, dict):
        diff = ca.get("brand_differentiation") or ca.get("differentiation") or ca.get("differentiators") or []
        if isinstance(diff, list):
            differentiators.extend([_safe_str(d) for d in diff if d])
    if len(differentiators) < 5 and insight:
        angles = getattr(insight, "messaging_angles", None) or []
        if isinstance(angles, list):
            for a in angles:
                txt = _safe_str(a)
                if txt and txt not in differentiators:
                    differentiators.append(txt)
                if len(differentiators) >= 5:
                    break
    for i in range(1, 6):
        r = _find_row_starting_with(ws, 1, f"Key Differentiator {i}", end=20)
        if r and i - 1 < len(differentiators):
            src = "competitor_analysis" if differentiators[i - 1] in (ca.get("brand_differentiation", []) if isinstance(ca, dict) else []) else "messaging_angles"
            note = "direct:competitor_analysis" if src == "competitor_analysis" else "derived:messaging_angles"
            _write_row_meta(ws, r, value=differentiators[i - 1], source=src, notes=note)

    # Key Value Props 1-5
    value_props = []
    if insight:
        vp = getattr(insight, "value_props", None) or []
        if isinstance(vp, list):
            value_props = [_safe_str(v) for v in vp if v][:5]
    for i in range(1, 6):
        r = _find_row_starting_with(ws, 1, f"Key Value Prop {i}", end=20)
        if r and i - 1 < len(value_props):
            _write_row_meta(ws, r, value=value_props[i - 1], source="insights", notes="direct:value_props")

    # Reasons to Believe
    r = _find_row_starting_with(ws, 1, "Reasons to Believe", end=20)
    if r:
        reasons: List[str] = []
        if insight:
            vq = getattr(insight, "verbatim_quotes", None) or []
            if isinstance(vq, list):
                for q in vq[:5]:
                    reasons.append(_safe_str(q))
        _write_row_meta(
            ws, r,
            value="\n".join(f"- {x}" for x in reasons if x),
            source="verbatim_quotes",
            notes=f"derived:top {len(reasons)} verbatim quotes",
        )


# =============================================================================
# Strategy Layer — CTP block (Angles / Pain Points / Desires / Segments / Frameworks / Hooks / Value Props / Formats / Visual Styles / Talent / Visual Hooks)
# =============================================================================

def _fill_ctp_block(
    ws: Worksheet,
    ctp_num: int,
    start_row: int,
    next_start_row: int,
    ctp: Dict[str, Any],
    ctp_hypothesis_entry: Optional[Dict[str, Any]],
    framework_counts: Dict[str, int],
    raw_analyzer_frameworks: List[Tuple[str, int]],
    top_formats: List[Tuple[str, int]],
    top_visual_styles: List[Tuple[str, int]],
    top_talent: List[Tuple[str, int]],
    top_visual_hooks: List[Tuple[str, int]],
    global_value_props: List[str],
    global_hooks: List[str],
    all_hooks_pool: List[str],
    all_value_props_pool: List[str],
    n_ads: int,
) -> None:
    """Fill a single CTP's block (rows from start_row to next_start_row - 1)."""

    # Update the section header row: replace "(Add CTP Name Here)" with actual name
    ctp_name = ctp.get("ctp_name", "")
    header_val = ws.cell(start_row, 1).value or ""
    if ctp_name and isinstance(header_val, str) and "Add CTP Name" in header_val:
        ws.cell(start_row, 1).value = header_val.replace("(Add CTP Name Here)", ctp_name)

    # CTP Name field row
    r = _find_row_starting_with(ws, 1, "CTP Name", start=start_row, end=next_start_row - 1)
    if r:
        _write_row_meta(
            ws, r, value=ctp_name,
            source="ctp_builder",
            notes=f"direct:ctp_data[{ctp_num-1}] weight={ctp.get('weight', '?')}, review%={ctp.get('review_percentage', '?')}",
        )

    # Core Insight — enriched with what_makes_them_unique
    r = _find_row_starting_with(ws, 1, "Core Insight", start=start_row, end=next_start_row - 1)
    if r:
        insight_text = ctp.get("core_insight_general") or ctp.get("core_insight_product_anchored") or ""
        unique = ctp.get("what_makes_them_unique", "")
        if unique:
            insight_text = f"{insight_text} — Unique: {unique}" if insight_text else unique
        _write_row_meta(ws, r, value=insight_text, source="ctp_builder", notes="direct:core_insight_general+what_makes_them_unique")

    # --- Angles 1-5 — primary source: ctp_hypothesis[i].angles (description/hypothesis/awareness)
    # Sub-table header (Angle row): col A="Angle", B=Hypothesis, C=Awareness Level, D=Validation, E=Notes
    angles = _build_angles_for_ctp(ctp, ctp_hypothesis_entry)
    for i in range(1, 6):
        r = _find_row_starting_with(ws, 1, f"Angle {i}", start=start_row, end=next_start_row - 1)
        if r and i - 1 < len(angles):
            description, hypothesis, awareness, source_tag = angles[i - 1]
            ws.cell(r, 1).value = description
            if hypothesis:
                _write(ws, r, 2, hypothesis)
            if awareness:
                _write(ws, r, 3, awareness)
            _write(ws, r, 4, "False")  # col D Validation
            _write(ws, r, 5, source_tag)  # col E Notes (origin tag)

    # --- Pain Points 1-3 (col A has prompt; replace) ---
    pain_points = ctp.get("pain_points") or []
    for i in range(1, 4):
        candidates = [f"Pain Point/ Desire {i}", f"Pain Point / Desire {i}", f"Pain Point {i}"]
        r = None
        for cand in candidates:
            r = _find_row_starting_with(ws, 1, cand, start=start_row, end=next_start_row - 1)
            if r:
                break
        if r and i - 1 < len(pain_points):
            pp = pain_points[i - 1]
            pp_text = pp.get("pain_point") if isinstance(pp, dict) else _safe_str(pp)
            ws.cell(r, 1).value = _safe_str(pp_text)
            # Row header: A=label, B=Source, C=Validation, D=Notes → write source+notes there
            _write(ws, r, 2, "ctp_builder")
            _write(ws, r, 4, f"direct:pain_points[{i-1}]")

    # --- Desires 1-3 — derive from ctp_hypothesis demographics + invert pain points ---
    desires = _build_desires_for_ctp(ctp, ctp_hypothesis_entry)
    # The template uses "Pain Point/ Desire 1..3" labels for pain points (already
    # filled above) and a separate set of labels for desires. We try several
    # common patterns and only write where col A still looks like a prompt placeholder.
    for i in range(1, 4):
        if i - 1 >= len(desires):
            break
        r = (
            _find_row_starting_with(ws, 1, f"Desire {i}", start=start_row, end=next_start_row - 1)
            or _find_row_starting_with(ws, 1, f"Customer Desire {i}", start=start_row, end=next_start_row - 1)
            or _find_row_starting_with(ws, 1, f"Aspiration {i}", start=start_row, end=next_start_row - 1)
        )
        if not r:
            continue
        # Only write if the cell still has the placeholder prompt or is GAP/empty —
        # never overwrite existing pain-point text or human input.
        existing = ws.cell(r, 1).value
        if existing and not _is_empty_or_gap(existing) and "desire" not in str(existing).lower():
            continue
        ws.cell(r, 1).value = _safe_str(desires[i - 1])
        _write(ws, r, 2, "ctp_hypothesis")
        _write(ws, r, 4, "derived:demographic_variables+pain_points")

    # --- Segments 1-3 — Fix 7: derive from ctp_hypothesis.demographic_variables ---
    # Convention (matches Pain Points sub-table): A=value, B=source, D=notes; col E checkbox stays.
    segments = _build_segments_from_demographics(ctp_hypothesis_entry)
    for i in range(1, 4):
        r = _find_row_starting_with(ws, 1, f"Segment {i}", start=start_row, end=next_start_row - 1)
        if r and i - 1 < len(segments):
            ws.cell(r, 1).value = segments[i - 1]
            _write(ws, r, 2, "ctp_hypothesis")
            _write(ws, r, 4, "direct:ctp_hypothesis.demographic_variables")

    # --- Frameworks (16 rows): fill ALL with creative directions ---
    notes_global = f"global_agg:ad_library_analyzer (N={n_ads} ads)"
    for fw_name in EXCEL_FRAMEWORKS:
        r = _find_row_starting_with(ws, 1, fw_name, start=start_row, end=next_start_row - 1)
        if not r:
            continue
        count = framework_counts.get(fw_name, 0)
        direction = _build_framework_direction(ctp, fw_name)
        if direction:
            source = "ad_library_analyzer" if count > 0 else "ctp_builder"
            notes = f"{notes_global}, fw_count={count}" if count > 0 else "ctp_context (no ads using this framework yet)"
            _write_row_meta(ws, r, value=direction, source=source, notes=notes)

    # --- Copy Hooks 1-3 — per-CTP ranking, fall back to global pool ---
    ctp_hooks, hooks_source = _select_hooks_for_ctp(ctp, ctp_hypothesis_entry, all_hooks_pool, global_hooks)
    for i in range(1, 4):
        r = _find_row_starting_with(ws, 1, f"Copy Hook {i}", start=start_row, end=next_start_row - 1)
        if r and i - 1 < len(ctp_hooks):
            ws.cell(r, 1).value = _safe_str(ctp_hooks[i - 1])
            _write(ws, r, 2, "hooks_library")
            _write(ws, r, 4, hooks_source)

    # --- Value Props 1-3 — per-CTP ranking, fall back to global pool ---
    ctp_value_props, vp_source = _select_value_props_for_ctp(ctp, all_value_props_pool, global_value_props)
    for i in range(1, 4):
        r = _find_row_starting_with(ws, 1, f"Value Prop {i}", start=start_row, end=next_start_row - 1)
        if r and i - 1 < len(ctp_value_props):
            ws.cell(r, 1).value = _safe_str(ctp_value_props[i - 1])
            _write(ws, r, 2, "insights")
            _write(ws, r, 4, vp_source)

    # --- Formats 1-3 — pad with CTP-aware suggestions when ad data is sparse ---
    ctp_formats = _enrich_execution_slots(top_formats, ctp, "format")
    _fill_ranked_slots(ws, "Format", ctp_formats, start_row, next_start_row, "ad_library_analyzer", notes_global)

    # --- Visual Styles 1-3 ---
    ctp_visual_styles = _enrich_execution_slots(top_visual_styles, ctp, "visual_style")
    _fill_ranked_slots(ws, "Visual Style", ctp_visual_styles, start_row, next_start_row, "ad_library_analyzer", notes_global)

    # --- Talent 1-3 ---
    ctp_talent = _enrich_execution_slots(top_talent, ctp, "talent")
    _fill_ranked_slots(ws, "Talent", ctp_talent, start_row, next_start_row, "ad_library_analyzer", notes_global)

    # --- Visual Hooks 1-3 ---
    _fill_ranked_slots(ws, "Visual Hook", top_visual_hooks, start_row, next_start_row, "ad_library_analyzer", notes_global)

    # --- Discovery v2 enrichments: anti-patterns + vocabulary in notes ---
    anti_patterns = ctp.get("anti_patterns", [])
    if anti_patterns and isinstance(anti_patterns, list):
        # Find an empty row near the end to place anti-patterns note, or use CTP Name notes col
        r = _find_row_starting_with(ws, 1, "CTP Name", start=start_row, end=next_start_row - 1)
        if r:
            existing_note = ws.cell(r, 5).value or ""
            anti_text = "DO NOT: " + "; ".join(_safe_str(a) for a in anti_patterns[:4])
            ws.cell(r, 5).value = f"{existing_note} | {anti_text}" if existing_note else anti_text

    vocabulary = ctp.get("vocabulary", [])
    if vocabulary and isinstance(vocabulary, list):
        # Add vocabulary to Core Insight notes col
        r = _find_row_starting_with(ws, 1, "Core Insight", start=start_row, end=next_start_row - 1)
        if r:
            existing_note = ws.cell(r, 5).value or ""
            vocab_text = "Vocabulary: " + ", ".join(_safe_str(v) for v in vocabulary[:8])
            ws.cell(r, 5).value = f"{existing_note} | {vocab_text}" if existing_note else vocab_text

    # Behavioral markers enrich segment descriptions
    markers = ctp.get("behavioral_markers", [])
    if markers and isinstance(markers, list):
        r = _find_row_starting_with(ws, 1, "Segment 1", start=start_row, end=next_start_row - 1)
        if r:
            existing_note = ws.cell(r, 4).value or ""
            markers_text = "Behaviors: " + "; ".join(_safe_str(m) for m in markers[:4])
            ws.cell(r, 4).value = f"{existing_note} | {markers_text}" if existing_note else markers_text


# CTP-aware fallback suggestions for execution testing slots.
# Used when the ad library has fewer than 3 entries for a dimension.
# Keyed by dimension → list of (value, pseudo_count) in priority order.
# These are common creative execution patterns — not brand-specific.
_EXECUTION_FALLBACKS: Dict[str, List[Tuple[str, int]]] = {
    "format": [
        ("Talking Head (UGC)", 0),
        ("Video Explainer (Educational Demo)", 0),
        ("Carousel / Swipe", 0),
        ("Single Image (Static)", 0),
        ("Brand Pitch", 0),
    ],
    "visual_style": [
        ("UGC → LOFI", 0),
        ("UGC → HIFI", 0),
        ("Graphic Design", 0),
        ("Elevated → cinematic, studio, premium", 0),
        ("Product Shot", 0),
    ],
    "talent": [
        ("Creator / Influencer", 0),
        ("Actor", 0),
        ("Founder / Expert", 0),
        ("Voiceover Only", 0),
        ("Brand Rep", 0),
    ],
}


def _enrich_execution_slots(
    ranked: List[Tuple[str, int]],
    ctp: Dict[str, Any],
    dimension: str,
) -> List[Tuple[str, int]]:
    """Pad a ranked execution list to at least 3 entries using CTP-aware fallbacks.

    When the ad library only found 1-2 entries (e.g. all static ads → only
    'Single Image'), this fills the remaining slots with common creative formats
    so the Excel never has unexplained empty gaps.
    """
    if len(ranked) >= 3:
        return ranked

    result = list(ranked)
    seen = {v.lower() for v, _ in result}

    # Use tone to prioritize: technical CTPs benefit from explainers,
    # emotional CTPs benefit from UGC/talking heads
    tone = ctp.get("tone_emotion_arc") or {}
    tone_str = str(tone.get("tone") or "").lower()

    fallbacks = _EXECUTION_FALLBACKS.get(dimension, [])
    # Reorder fallbacks: if CTP tone is technical/precise, prefer explainer/expert;
    # if emotional/relatable, prefer UGC/creator
    if "technical" in tone_str or "precise" in tone_str or "authoritative" in tone_str:
        # Boost explainer/expert formats to top
        fallbacks = sorted(fallbacks, key=lambda x: 0 if any(
            kw in x[0].lower() for kw in ("explainer", "expert", "founder", "elevated")
        ) else 1)
    elif "relatable" in tone_str or "casual" in tone_str or "raw" in tone_str:
        # Boost UGC/creator formats to top
        fallbacks = sorted(fallbacks, key=lambda x: 0 if any(
            kw in x[0].lower() for kw in ("ugc", "creator", "talking", "lofi")
        ) else 1)

    for val, count in fallbacks:
        if val.lower() not in seen:
            result.append((val, count))
            seen.add(val.lower())
        if len(result) >= 3:
            break

    return result[:3]


def _fill_ranked_slots(
    ws: Worksheet,
    label_prefix: str,
    ranked: List[Tuple[str, int]],
    start_row: int,
    next_start_row: int,
    source: str,
    notes: str,
) -> None:
    """Fill 3 slots named '{label_prefix} 1', '{label_prefix} 2', '{label_prefix} 3'."""
    for i in range(1, 4):
        r = _find_row_starting_with(ws, 1, f"{label_prefix} {i}", start=start_row, end=next_start_row - 1)
        if not r:
            continue
        if i - 1 < len(ranked):
            val, count = ranked[i - 1]
            ws.cell(r, 1).value = _safe_str(val)
            _write(ws, r, 2, source)
            _write(ws, r, 4, f"{notes}, count={count}")
        else:
            # Mark unfilled slots so users know it's a gap, not an oversight
            ws.cell(r, 1).value = "GAP — insufficient ad data"
            _write(ws, r, 2, source)
            _write(ws, r, 4, f"{notes}, count=0 (no additional data)")


def _compose_hypothesis_fallback(
    ctp: Dict[str, Any],
    angle_text: str,
) -> str:
    """Build a hypothesis sentence from CTP signals when ctp_hypothesis is sparse.

    Used when validation_evidence/emotional_trigger/validation_tag are all empty,
    or when we're falling back to barriers/objections (which carry no hypothesis
    of their own). Anchors the hypothesis in the CTP's core insight + top
    blocker/trigger so it's still actionable instead of empty.
    """
    core = ctp.get("core_insight_general") or ctp.get("core_insight_product_anchored") or ""
    core = core.strip()
    blockers = ctp.get("blocker_distribution") or {}
    triggers = ctp.get("trigger_distribution") or {}

    top_blocker = ""
    if isinstance(blockers, dict) and blockers:
        top_blocker = max(blockers.items(), key=lambda kv: kv[1])[0]
    top_trigger = ""
    if isinstance(triggers, dict) and triggers:
        top_trigger = max(triggers.items(), key=lambda kv: kv[1])[0]

    parts: List[str] = []
    if core:
        short_core = core if len(core) < 140 else core[:137] + "..."
        parts.append(f"Speaks to: \"{short_core}\"")
    if top_trigger:
        parts.append(f"Activates trigger: {top_trigger}")
    if top_blocker:
        parts.append(f"Defuses blocker: {top_blocker}")
    if not parts and angle_text:
        # Last resort: at least describe the angle's intent
        parts.append(f"Intended to address: {angle_text[:120]}")
    return " — ".join(parts)


def _build_angles_for_ctp(
    ctp: Dict[str, Any],
    ctp_hypothesis_entry: Optional[Dict[str, Any]],
) -> List[Tuple[str, str, str, str]]:
    """
    Compose up to 5 angle entries (description, hypothesis, awareness_level, source_tag).

    Primary source: ctp_hypothesis_entry.angles (rich structure with description + evidence + awareness).
    Fallback (if < 5): barriers_objections.prompt — but with hypothesis composed from the CTP's
    core insight + top trigger/blocker instead of left blank.
    """
    angles: List[Tuple[str, str, str, str]] = []

    # Primary: ctp_hypothesis.angles (already structured with awareness + evidence)
    if isinstance(ctp_hypothesis_entry, dict):
        hyp_angles = ctp_hypothesis_entry.get("angles") or []
        if isinstance(hyp_angles, list):
            for ha in hyp_angles:
                if not isinstance(ha, dict):
                    continue
                description = ha.get("angle_description") or ha.get("angle_name") or ""
                if not description:
                    continue
                # Compose hypothesis from validation_evidence + emotional_trigger if available
                evidence = ha.get("validation_evidence") or ""
                emotional = ha.get("emotional_trigger") or ""
                tag = ha.get("validation_tag") or ""
                hyp_parts = [p for p in [evidence, f"Trigger: {emotional}" if emotional else "", f"({tag})" if tag else ""] if p]
                hypothesis = " — ".join(hyp_parts)
                # Fallback: if the hypothesis fields were all empty, derive one from CTP signals
                source_tag = "direct:ctp_hypothesis.angles"
                if not hypothesis:
                    hypothesis = _compose_hypothesis_fallback(ctp, description)
                    if hypothesis:
                        source_tag = "ctp_hypothesis.angles + derived:core_insight"
                awareness = ha.get("awareness_level") or ""
                angles.append((description, hypothesis, awareness, source_tag))
                if len(angles) >= 5:
                    break

    # Fallback: barriers_objections — now WITH a derived hypothesis instead of empty
    if len(angles) < 5:
        barriers = ctp.get("barriers_objections") or []
        for b in barriers:
            if isinstance(b, dict):
                txt = b.get("prompt") or b.get("barrier") or b.get("objection") or b.get("text")
            elif isinstance(b, str):
                txt = b
            else:
                txt = ""
            txt = str(txt or "").strip()
            if not txt or any(txt == a[0] for a in angles):
                continue
            hypothesis = _compose_hypothesis_fallback(ctp, txt)
            angles.append((txt, hypothesis, "", "fallback:ctp.barriers_objections + derived:core_insight"))
            if len(angles) >= 5:
                break

    return angles[:5]


def _build_desires_for_ctp(
    ctp: Dict[str, Any],
    ctp_hypothesis_entry: Optional[Dict[str, Any]],
) -> List[str]:
    """Surface 3 desires for a CTP, preferring LLM-generated content.

    Source priority:
      1. ctp.desires            (NEW: LLM emits these per CTP, grounded in snippets+brand context)
      2. ctp_hypothesis.demographic_variables.aspirations
      3. raw pain_points (unmodified — prefer honest "they hate X" over invented "they want not-X")

    No hardcoded English-prefix inversions, no template phrasing. If the LLM
    didn't supply desires AND there's no aspirations field, the slot stays
    empty rather than getting filled with generic "Resolve: <pain>" stubs.
    """
    desires: List[str] = []
    seen: set = set()

    def _add(text: str) -> None:
        t = (text or "").strip()
        if not t:
            return
        key = t.lower()
        if key in seen:
            return
        seen.add(key)
        desires.append(t)

    # 1) Native CTP desires from the LLM (the canonical source going forward)
    for d in ctp.get("desires") or []:
        if isinstance(d, dict):
            _add(d.get("desire") or d.get("text") or _safe_str(d))
        else:
            _add(_safe_str(d))
        if len(desires) >= 3:
            break

    # 2) Hypothesis-layer aspirations (also LLM-generated, but at the strategy level)
    if len(desires) < 3 and isinstance(ctp_hypothesis_entry, dict):
        demo = ctp_hypothesis_entry.get("demographic_variables") or {}
        if isinstance(demo, dict):
            asp = demo.get("aspirations") or demo.get("desires") or []
            if isinstance(asp, list):
                for a in asp:
                    _add(_safe_str(a))
                    if len(desires) >= 3:
                        break
            elif isinstance(asp, str):
                _add(asp)

    return desires[:3]


def _build_segments_from_demographics(ctp_hypothesis_entry: Optional[Dict[str, Any]]) -> List[str]:
    """Compose up to 3 segment descriptors from ctp_hypothesis.demographic_variables.

    The three segments map to the template's Demographic / Behavioral / Psychographic slots:
      1. Demographic: age, gender, income, education, geo
      2. Behavioral: platforms, lifestyle markers
      3. Psychographic: aspirations, combined with age for context
    Each segment is built from DIFFERENT fields to avoid duplication.
    """
    if not isinstance(ctp_hypothesis_entry, dict):
        return []
    demo = ctp_hypothesis_entry.get("demographic_variables") or {}
    if not isinstance(demo, dict):
        return []
    age = demo.get("age_range") or ""
    gender = demo.get("gender_skew") or ""
    income = demo.get("income_level") or ""
    education = demo.get("education") or ""
    platforms = demo.get("platform_affinity") or []
    if isinstance(platforms, str):
        platforms = [p.strip() for p in platforms.split(",")]
    geo = demo.get("geo_notes") or ""
    aspirations = demo.get("aspirations") or ""
    lifestyle = demo.get("lifestyle_markers") or ""
    if isinstance(lifestyle, list):
        lifestyle = ", ".join(lifestyle[:3])

    segments: List[str] = []

    # Segment 1 — Demographic: age + gender + income/education + geo
    demo_parts = [p for p in [age, gender] if p]
    if income:
        demo_parts.append(f"{income} income")
    if education:
        demo_parts.append(f"{education}")
    if geo:
        demo_parts.append(geo)
    if demo_parts:
        segments.append("Demographic: " + " / ".join(demo_parts))

    # Segment 2 — Behavioral: platforms + lifestyle
    behav_parts = []
    if platforms:
        behav_parts.append("Active on " + ", ".join(platforms[:3]))
    if lifestyle:
        behav_parts.append(lifestyle)
    if behav_parts:
        segments.append("Behavioral: " + " / ".join(behav_parts))
    elif age:
        segments.append(f"Behavioral: {age} / digital-first research behavior")

    # Segment 3 — Psychographic: aspirations
    if aspirations:
        if isinstance(aspirations, list):
            aspirations = "; ".join(aspirations[:3])
        segments.append(f"Psychographic: {aspirations}")
    elif segments:
        # Fallback: derive from CTP pain points if available
        segments.append("Psychographic: value-driven, research-heavy decision maker")

    return segments[:3]


def _select_hooks_for_ctp(
    ctp: Dict[str, Any],
    ctp_hypothesis_entry: Optional[Dict[str, Any]],  # noqa: ARG001 (kept for callers; LLM does the work upstream now)
    pool: List[str],
    fallback_hooks: List[str],
) -> Tuple[List[str], str]:
    """Surface 3 hooks for a CTP, preferring LLM-generated content.

    Source priority:
      1. ctp.recommended_hooks   (LLM picks/writes these per CTP, source-tagged)
      2. brand-level pool        (only if LLM didn't supply 3)
      3. global recommended_hooks fallback (only if pool is also short)

    No keyword matching. The LLM has already done the relevance work upstream
    using the full brand_context block + this CTP's snippets, pain points,
    language cues, and stance. Re-ranking here would just throw that away.
    """
    selected: List[Tuple[str, str]] = []  # (hook_text, source_tag)
    seen: set = set()

    def _add(text: str, tag: str) -> None:
        t = (text or "").strip()
        if not t or t.lower() in seen:
            return
        seen.add(t.lower())
        selected.append((t, tag))

    # 1) Native per-CTP hooks from the LLM (source-tagged from_brand_library or new_for_this_ctp)
    for h in ctp.get("recommended_hooks") or []:
        if isinstance(h, dict):
            _add(h.get("hook") or h.get("text"), h.get("source") or "ctp_llm")
        else:
            _add(_safe_str(h), "ctp_llm")
        if len(selected) >= 3:
            break

    # 2) Top up from the per-CTP brand pool (preserves order — already brand-prioritized)
    if len(selected) < 3:
        for h in pool or []:
            _add(_safe_str(h), "brand_pool_fallback")
            if len(selected) >= 3:
                break

    # 3) Last resort: global recommended_hooks
    if len(selected) < 3:
        for h in fallback_hooks or []:
            _add(_safe_str(h), "global_fallback")
            if len(selected) >= 3:
                break

    hooks = [t for t, _ in selected[:3]]
    sources = "+".join(sorted({tag for _, tag in selected[:3]})) or "empty"
    return (hooks, f"ctp.recommended_hooks ({sources})")


def _select_value_props_for_ctp(
    ctp: Dict[str, Any],
    pool: List[str],  # noqa: ARG001 (kept for back-compat; LLM already ranked relative to brand pool upstream)
    fallback_vps: List[str],
) -> Tuple[List[str], str]:
    """Surface 3 value props for a CTP, preferring LLM-generated content.

    Source priority:
      1. ctp.recommended_value_props (LLM picks/writes these per CTP)
      2. global value_props fallback

    No token-overlap ranking — the LLM had the full brand context and snippets
    when picking these, which beats keyword matching.
    """
    selected: List[Tuple[str, str]] = []
    seen: set = set()

    def _add(text: str, tag: str) -> None:
        t = (text or "").strip()
        if not t or t.lower() in seen:
            return
        seen.add(t.lower())
        selected.append((t, tag))

    for v in ctp.get("recommended_value_props") or []:
        if isinstance(v, dict):
            _add(v.get("value_prop") or v.get("text"), v.get("source") or "ctp_llm")
        else:
            _add(_safe_str(v), "ctp_llm")
        if len(selected) >= 3:
            break

    if len(selected) < 3:
        for v in fallback_vps or []:
            _add(_safe_str(v), "global_fallback")
            if len(selected) >= 3:
                break

    vps = [t for t, _ in selected[:3]]
    sources = "+".join(sorted({tag for _, tag in selected[:3]})) or "empty"
    return (vps, f"ctp.recommended_value_props ({sources})")


def _build_framework_direction(ctp: Dict[str, Any], framework_name: str) -> str:
    """Short 1-line creative direction combining CTP core insight + framework + ad gap.

    If this CTP has a matching entry in frameworks_that_resonate, use the LLM's
    rationale instead of the generic template — it's already grounded in the
    CTP's snippets and pain points.
    """
    # Check if the LLM already wrote a per-CTP rationale for a resonant framework
    for ftr in ctp.get("frameworks_that_resonate") or []:
        if not isinstance(ftr, dict):
            continue
        fw_name = (ftr.get("framework") or "").strip()
        rationale = (ftr.get("rationale") or "").strip()
        # Fuzzy match: the LLM framework name may not match the Excel label exactly
        if rationale and (
            framework_name.lower() in fw_name.lower()
            or fw_name.lower() in framework_name.lower()
        ):
            rationale_short = rationale if len(rationale) < 250 else rationale[:247] + "..."
            return f"{framework_name}: {rationale_short}"

    core = ctp.get("core_insight_general") or ctp.get("core_insight_product_anchored") or "this CTP's core insight"
    core_short = core if len(core) < 140 else core[:137] + "..."
    ad_gap = ctp.get("ad_creative_gap", "")
    direction = f"Use the '{framework_name}' framework to dramatize: {core_short}"
    if ad_gap:
        gap_short = ad_gap if len(ad_gap) < 100 else ad_gap[:97] + "..."
        direction += f" | Gap to exploit: {gap_short}"
    return direction


# =============================================================================
# CTP Backlog sheet
# =============================================================================

def _fill_ctp_backlog(ws: Worksheet, ctps: List[Dict[str, Any]], session_date: str) -> None:
    """CTPs ranked 4..10 go here. Fix 4: rank by review_percentage (or snippet_count) when available."""
    parked = ctps[3:10]
    header_row = _find_row_starting_with(ws, 1, "#", end=5)
    if not header_row:
        return
    first_data_row = header_row + 1
    for idx, ctp in enumerate(parked):
        r = first_data_row + idx
        _write(ws, r, 2, ctp.get("ctp_name"))
        insight_text = ctp.get("core_insight_general") or ctp.get("core_insight_product_anchored") or ""
        _write(ws, r, 3, insight_text)
        _write(ws, r, 4, "SCRAPPER auto-fill")
        # Fix 4: prefer review_percentage; fall back to snippet_count, then weight
        rank_value = ctp.get("review_percentage")
        rank_label = "review_%"
        if rank_value is None:
            rank_value = ctp.get("snippet_count")
            rank_label = "snippet_count"
        if rank_value is None:
            rank_value = ctp.get("weight")
            rank_label = "weight"
        _write(ws, r, 5, rank_value)
        _write(ws, r, 6, "Below top-3 threshold")
        _write(ws, r, 9, f"ctp_builder rank {idx + 4} ({rank_label})")
        _write(ws, r, 10, session_date)


# =============================================================================
# Creative Info sheet (CBG)
# =============================================================================

def _fill_creative_info(ws: Worksheet, brand: Any) -> None:
    """Fill the Client Brand Guidelines block."""
    fonts = brand.fonts or []
    if isinstance(fonts, list):
        r = _find_row_starting_with(ws, 1, "Font — Primary") or _find_row_starting_with(ws, 1, "Font - Primary") or _find_row_starting_with(ws, 1, "Font — Primary")
        if r and len(fonts) >= 1:
            _write(ws, r, 2, fonts[0])
        r = _find_row_starting_with(ws, 1, "Font — Secondary") or _find_row_starting_with(ws, 1, "Font - Secondary") or _find_row_starting_with(ws, 1, "Font — Secondary")
        if r and len(fonts) >= 2:
            _write(ws, r, 2, fonts[1])

    colors = brand.brand_colors or []
    if isinstance(colors, list):
        slots = ["Color Palette — Primary", "Color Palette — Secondary", "Color Palette — Accent"]
        for i, slot_label in enumerate(slots):
            r = _find_row_starting_with(ws, 1, slot_label) or _find_row_starting_with(ws, 1, slot_label.replace("—", "-"))
            if r and i < len(colors):
                _write(ws, r, 2, colors[i])

    if brand.logo_url:
        r = _find_row_starting_with(ws, 1, "Logo — Primary") or _find_row_starting_with(ws, 1, "Logo - Primary") or _find_row_starting_with(ws, 1, "Logo — Primary")
        if r:
            _write(ws, r, 3, brand.logo_url)  # col C = Link / File

    # Brand Persona
    r = _find_row_starting_with(ws, 1, "Brand Persona")
    if r:
        aesthetic = brand.brand_aesthetic or []
        values = brand.brand_values or []
        parts = []
        if isinstance(aesthetic, list) and aesthetic:
            parts.append("Aesthetic: " + ", ".join(_safe_str(a) for a in aesthetic))
        if isinstance(values, list) and values:
            parts.append("Values: " + ", ".join(_safe_str(v) for v in values))
        if parts:
            _write(ws, r, 2, "; ".join(parts))

    # Creative Direction Statement
    r = _find_row_starting_with(ws, 1, "Creative Direction Statement")
    if r:
        aesthetic = brand.brand_aesthetic or []
        tone = brand.tone_of_voice or []
        if isinstance(aesthetic, list) and isinstance(tone, list) and (aesthetic or tone):
            statement = f"The brand reads as {', '.join(_safe_str(a) for a in aesthetic)} with a {', '.join(_safe_str(t) for t in tone)} tone."
            _write(ws, r, 2, statement)

    # Tone of Voice Summary
    r = _find_row_starting_with(ws, 1, "Tone of Voice Summary")
    if r:
        tone = brand.tone_of_voice or []
        if isinstance(tone, list) and tone:
            _write(ws, r, 2, ", ".join(_safe_str(t) for t in tone))

    # Moodboard: enumerate brand_images (Fix 3: only public http(s) URLs — drop internal /api/ paths)
    moodboard_header_row = _find_row_starting_with(ws, 1, "Image / Reference")
    if moodboard_header_row and isinstance(brand.brand_images, list):
        public_imgs = [
            u for u in brand.brand_images
            if isinstance(u, str) and u.lower().startswith(("http://", "https://"))
        ]
        for i, img_url in enumerate(public_imgs[:5]):
            r = moodboard_header_row + 1 + i
            if r > ws.max_row:
                break
            _write(ws, r, 1, f"Brand image {i + 1}")
            _write(ws, r, 2, img_url)


# =============================================================================
# Performance - Concepts sheet: pre-populate CTP names on first 3 rows
# =============================================================================

def _fill_performance_concepts(ws: Worksheet, ctps: List[Dict[str, Any]]) -> None:
    """Prefill the 'CTP Name (from Strategy)' col D for rows C-001/002/003."""
    header_row = _find_row_starting_with(ws, 1, "Concept ID", end=5)
    if not header_row:
        return
    first_data_row = header_row + 1
    for i, ctp in enumerate(ctps[:3]):
        r = first_data_row + i
        _write(ws, r, 4, ctp.get("ctp_name"), overwrite_non_gap=False)


# =============================================================================
# Operational sheet: pre-populate Output Specs with industry defaults (Fix 6)
# =============================================================================

# Standard creative specs per ad platform — these are stable industry defaults
# and don't change per scrape. Source: Meta/TikTok/Google/YT public ad specs.
OUTPUT_SPECS_DEFAULTS: Dict[str, Dict[str, str]] = {
    "Meta (Feed)": {"format": "Square / Vertical", "aspect": "1:1, 4:5", "safe_zone": "250px top/bottom", "max_duration": "60s", "file_type": "MP4, MOV"},
    "Meta (Stories/Reels)": {"format": "Vertical Full-Screen", "aspect": "9:16", "safe_zone": "14% top, 20% bottom", "max_duration": "90s", "file_type": "MP4, MOV"},
    "TikTok": {"format": "Vertical Full-Screen", "aspect": "9:16", "safe_zone": "Top 130px, bottom 484px", "max_duration": "60s (10m max)", "file_type": "MP4, MOV"},
    "YouTube (Pre-roll)": {"format": "Horizontal", "aspect": "16:9", "safe_zone": "n/a", "max_duration": "30s (skippable 6s)", "file_type": "MP4, MOV, AVI"},
    "YouTube (Shorts)": {"format": "Vertical Full-Screen", "aspect": "9:16", "safe_zone": "Top 12%", "max_duration": "60s", "file_type": "MP4"},
    "Google Display": {"format": "Banner / Static", "aspect": "varies (300x250, 728x90, ...)", "safe_zone": "n/a", "max_duration": "n/a", "file_type": "JPG, PNG, GIF, HTML5"},
    "CTV/OTT": {"format": "Horizontal", "aspect": "16:9", "safe_zone": "5% safe area", "max_duration": "15s, 30s, 60s", "file_type": "MP4 (1080p)"},
}


def _fill_operational_output_specs(ws: Worksheet) -> None:
    """Pre-fill the Output Specs table with industry-standard defaults."""
    for platform, specs in OUTPUT_SPECS_DEFAULTS.items():
        r = _find_row_starting_with(ws, 1, platform)
        if not r:
            continue
        # Template columns: A=Platform, B=Format, C=Aspect Ratio, D=Safe Zone, E=Max Duration, F=File Type, G=Notes
        _write(ws, r, 2, specs["format"])
        _write(ws, r, 3, specs["aspect"])
        _write(ws, r, 4, specs["safe_zone"])
        _write(ws, r, 5, specs["max_duration"])
        _write(ws, r, 6, specs["file_type"])
        _write(ws, r, 7, "industry_defaults — verify per campaign")


# =============================================================================
# Target Personas sheet (NEW — April 2026 refactor)
# =============================================================================

def _fill_target_personas_sheet(wb: Any, insight: Any) -> None:
    """Create and populate a Target Personas sheet with TOFU prospect data."""
    target_personas = getattr(insight, 'target_personas', None) or []
    if not target_personas or not isinstance(target_personas, list):
        return

    # Create sheet if it doesn't exist
    sheet_name = "Target Personas"
    if sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
    else:
        ws = wb.create_sheet(sheet_name)

    # Header row
    headers = [
        "Name", "Awareness Level", "Problem They Have", "Why Not Yet a Customer",
        "Current Workaround", "What Would Unlock Them", "Acquisition Hook",
        "Format Recommendation", "Anti-Pattern", "Acquisition Difficulty",
        "Addressable Market %", "Demographics"
    ]
    for col, header in enumerate(headers, 1):
        ws.cell(1, col).value = header

    # Data rows
    for row_idx, tp in enumerate(target_personas, 2):
        if not isinstance(tp, dict):
            continue
        ws.cell(row_idx, 1).value = _safe_str(tp.get("name", ""))
        ws.cell(row_idx, 2).value = _safe_str(tp.get("awareness_level", ""))
        ws.cell(row_idx, 3).value = _safe_str(tp.get("the_problem_they_have", ""))
        ws.cell(row_idx, 4).value = _safe_str(tp.get("why_not_yet_a_customer", ""))
        ws.cell(row_idx, 5).value = _safe_str(tp.get("current_solution_or_workaround", ""))
        ws.cell(row_idx, 6).value = _safe_str(tp.get("what_would_unlock_them", ""))
        ws.cell(row_idx, 7).value = _safe_str(tp.get("acquisition_hook", ""))
        ws.cell(row_idx, 8).value = _safe_str(tp.get("creative_format_recommendation", ""))
        ws.cell(row_idx, 9).value = _safe_str(tp.get("anti_pattern", ""))
        ws.cell(row_idx, 10).value = _safe_str(tp.get("estimated_acquisition_difficulty", ""))
        ws.cell(row_idx, 11).value = _safe_str(tp.get("estimated_share_of_addressable_market", ""))
        # Demographics as compact string
        demo = tp.get("demographic_hypothesis", {})
        if isinstance(demo, dict) and demo:
            demo_parts = [f"{k}: {v}" for k, v in demo.items() if v]
            ws.cell(row_idx, 12).value = " | ".join(demo_parts)

    # Auto-width (approximate)
    for col in range(1, len(headers) + 1):
        ws.column_dimensions[chr(64 + col) if col <= 26 else "A"].width = 25


# =============================================================================
# Main entry
# =============================================================================

def build_rsw_database_export(brand: Any, insight: Any, scraped_data: List[Any]) -> bytes:
    """Render the Ready Set Way Database xlsx for a research session."""
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"RSW template not found at {TEMPLATE_PATH}")

    wb = load_workbook(TEMPLATE_PATH)

    # --- Prepare aggregated data ---
    ctps: List[Dict[str, Any]] = []
    ctp_hypotheses: List[Optional[Dict[str, Any]]] = []
    if insight:
        raw_ctps = getattr(insight, "ctp_data", None) or []
        raw_hyps = getattr(insight, "ctp_hypothesis", None) or []

        if isinstance(raw_ctps, list):
            indexed = [(i, c) for i, c in enumerate(raw_ctps) if isinstance(c, dict)]
            # Fix 4: rank by review_percentage when available, fallback to snippet_count, then weight
            def _rank_key(item):
                _, c = item
                return (
                    c.get("review_percentage") or 0,
                    c.get("snippet_count") or 0,
                    c.get("weight") or 0,
                )
            indexed.sort(key=_rank_key, reverse=True)
            ctps = [c for _, c in indexed]
            # Pair each sorted ctp with its hypothesis entry from the original list (parallel by original index)
            if isinstance(raw_hyps, list):
                ctp_hypotheses = [
                    raw_hyps[orig_i] if orig_i < len(raw_hyps) and isinstance(raw_hyps[orig_i], dict) else None
                    for orig_i, _ in indexed
                ]
            else:
                ctp_hypotheses = [None] * len(ctps)

    ad_library = getattr(insight, "ad_library_data", None) if insight else None
    dim_counts = _aggregate_creative_dims(ad_library)
    raw_analyzer_frameworks = dim_counts.get("framework", [])
    framework_counts = _top_frameworks_for_excel(raw_analyzer_frameworks)
    top_formats = dim_counts.get("creative_format", [])
    top_visual_styles = dim_counts.get("visual_type", [])
    top_talent = dim_counts.get("talent_type", [])
    top_visual_hooks = dim_counts.get("first_frame_element", []) or dim_counts.get("opener_visual_description", [])
    n_ads_analyzed = sum(c for _, c in raw_analyzer_frameworks) or 0

    global_value_props: List[str] = []
    global_hooks: List[str] = []
    # Full pools used for per-CTP relevance ranking (not capped at 3).
    all_value_props_pool: List[str] = []
    all_hooks_pool: List[str] = []
    if insight:
        vp = getattr(insight, "value_props", None) or []
        if isinstance(vp, list):
            all_value_props_pool = [_safe_str(v) for v in vp if v]
            global_value_props = all_value_props_pool[:3]
        hooks = getattr(insight, "recommended_hooks", None) or []
        if isinstance(hooks, list):
            all_hooks_pool = [_safe_str(h) for h in hooks if h]
            global_hooks = all_hooks_pool[:3]
        # Append the broader hooks_library (deduped) to the per-CTP pool, but keep
        # the top of recommended_hooks as the global fallback.
        hl = getattr(insight, "hooks_library", None) or []
        if isinstance(hl, list):
            for h in hl:
                txt = _safe_str(h)
                if txt and txt not in all_hooks_pool:
                    all_hooks_pool.append(txt)
                if txt and txt not in global_hooks and len(global_hooks) < 3:
                    global_hooks.append(txt)

    # --- Strategy Layer ---
    if "Strategy Layer" in wb.sheetnames:
        ws = wb["Strategy Layer"]
        _fill_brand_information(ws, brand, insight)

        anchors = _find_ctp_anchors(ws)

        # Clone extra CTP blocks if we have more CTPs than template slots
        if anchors and len(ctps) > len(anchors):
            last_n, last_start = anchors[-1]
            last_end = ws.max_row + 1
            for extra_idx in range(len(anchors), len(ctps)):
                new_n = extra_idx + 1
                new_start = _clone_ctp_block(ws, last_start, last_end, new_n)
                anchors.append((new_n, new_start))
                last_start = new_start
                last_end = ws.max_row + 1
            # Re-discover to pick up cloned blocks cleanly
            anchors = _find_ctp_anchors(ws)

        if anchors:
            # Build (ctp_num, start, end) tuples
            boundaries = []
            for i, (n, r) in enumerate(anchors):
                end = anchors[i + 1][1] if i + 1 < len(anchors) else ws.max_row + 1
                boundaries.append((n, r, end))
            for n, start, end in boundaries:
                if n - 1 < len(ctps):
                    hyp_entry = ctp_hypotheses[n - 1] if n - 1 < len(ctp_hypotheses) else None
                    _fill_ctp_block(
                        ws,
                        n,
                        start,
                        end,
                        ctps[n - 1],
                        hyp_entry,
                        framework_counts,
                        raw_analyzer_frameworks,
                        top_formats,
                        top_visual_styles,
                        top_talent,
                        top_visual_hooks,
                        global_value_props,
                        global_hooks,
                        all_hooks_pool,
                        all_value_props_pool,
                        n_ads_analyzed,
                    )

    # --- CTP Backlog ---
    if "CTP Backlog" in wb.sheetnames:
        session_date = datetime.utcnow().strftime("%Y-%m-%d")
        _fill_ctp_backlog(wb["CTP Backlog"], ctps, session_date)

    # --- Creative Info ---
    if "Creative Info" in wb.sheetnames:
        _fill_creative_info(wb["Creative Info"], brand)

    # --- Performance - Concepts ---
    if "Performance - Concepts" in wb.sheetnames:
        _fill_performance_concepts(wb["Performance - Concepts"], ctps)

    # --- Operational: Output Specs (industry defaults) ---
    if "Operational" in wb.sheetnames:
        _fill_operational_output_specs(wb["Operational"])

    # --- Target Personas (NEW) ---
    if insight:
        _fill_target_personas_sheet(wb, insight)

    # Stream to bytes
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
