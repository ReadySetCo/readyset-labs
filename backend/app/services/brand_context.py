"""
Build a rich, data-driven brand context block to ground LLM prompts.

The CTP pipeline used to classify snippets blindly with a hair-loss-flavored
prompt, which is why the same archetype names ("The Skeptic", "The Bio-Hacker")
came out on every brand. This module aggregates everything we already know
about a brand BEFORE running stance classification — VoC signals, brand DNA,
ad-library patterns, competitor positioning, per-source vocabulary — and renders
it as a single structured block that the prompts can interpolate.

There is no fixed schema or hardcoded vocabulary here. Every field is derived
from data the scraper already produced. If a field is empty in the input,
it's omitted from the output rather than substituted with a placeholder.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Iterable, List, Optional


# ---------------------------------------------------------------------------
# Tiny helpers (no LLM calls, no domain knowledge)
# ---------------------------------------------------------------------------

def _stringify(value: Any, max_len: int = 240) -> str:
    """Render any value as a single-line string capped at max_len."""
    if value is None:
        return ""
    if isinstance(value, dict):
        # Common payload shapes: {"text": ...}, {"pain_point": ...}, {"name": ...}
        for key in ("text", "value", "pain_point", "name", "title", "quote",
                    "hook", "angle", "objection", "trigger", "desire"):
            if key in value and value[key]:
                return str(value[key])[:max_len].strip()
        return str(value)[:max_len].strip()
    if isinstance(value, (list, tuple)):
        parts = [_stringify(v, max_len) for v in value]
        return "; ".join(p for p in parts if p)[:max_len]
    return str(value)[:max_len].strip()


def _top_strings(items: Iterable[Any], n: int = 5) -> List[str]:
    """Coerce a list of items into top-n distinct non-empty strings."""
    out: List[str] = []
    seen: set = set()
    for it in items or []:
        s = _stringify(it)
        if not s:
            continue
        key = s.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
        if len(out) >= n:
            break
    return out


def _bullet(items: Iterable[str], indent: str = "  - ") -> str:
    rendered = [f"{indent}{s}" for s in items if s]
    return "\n".join(rendered)


# ---------------------------------------------------------------------------
# Per-source vocabulary (so the prompt sees what Reddit says vs what Trustpilot says)
# ---------------------------------------------------------------------------

def per_source_voice(snippets: List[Dict[str, Any]], max_per_source: int = 2,
                     max_total_sources: int = 6) -> List[Dict[str, Any]]:
    """For each source_type, pick the most representative snippets.

    "Representative" = highest stance_confidence if available, else longest.
    Returns a list of {source_type, count, samples: [...]} dicts.
    """
    by_source: Dict[str, List[Dict[str, Any]]] = {}
    for s in snippets or []:
        src = s.get("source_type") or "unknown"
        by_source.setdefault(src, []).append(s)

    def rank(item):
        conf = item.get("stance_confidence") or 0
        length = len(item.get("content") or "")
        return (conf, length)

    ordered = sorted(by_source.items(), key=lambda kv: -len(kv[1]))[:max_total_sources]
    out: List[Dict[str, Any]] = []
    for src, group in ordered:
        ranked = sorted(group, key=rank, reverse=True)
        samples = []
        for s in ranked[:max_per_source]:
            txt = (s.get("content") or "").strip().replace("\n", " ")
            if len(txt) > 200:
                txt = txt[:197] + "..."
            samples.append(txt)
        out.append({"source_type": src, "count": len(group), "samples": samples})
    return out


# ---------------------------------------------------------------------------
# Tag distributions from the intake engine
# ---------------------------------------------------------------------------

def _aggregate_tag_distributions(snippets: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """Surface what the intake engine already classified across the VoC corpus.

    These are not stance-related — they're the orthogonal trigger/blocker/
    proof-type tags that snippet_classifier put on every row. Surfacing them
    in the brand_context lets the stance classifier and CTP refiner ground
    their interpretation in actual customer behavior signals (e.g., "this
    audience predominantly distrusts vet_science but trusts before_after").
    """
    triggers: Counter = Counter()
    blockers: Counter = Counter()
    proofs: Counter = Counter()
    outcomes: Counter = Counter()
    cues: Counter = Counter()

    for s in snippets or []:
        t = s.get("primary_trigger")
        if t:
            triggers[t] += 1
        b = s.get("blocker_type")
        if b:
            blockers[b] += 1
        p = s.get("proof_type_trusted")
        if p:
            proofs[p] += 1
        o = s.get("desired_outcome_level")
        if o:
            outcomes[o] += 1
        cs = s.get("language_cues") or []
        if isinstance(cs, list):
            for c in cs:
                if c:
                    cues[str(c)] += 1

    return {
        "triggers": [f"{k} ({v})" for k, v in triggers.most_common(6)],
        "blockers": [f"{k} ({v})" for k, v in blockers.most_common(6)],
        "proof_types": [f"{k} ({v})" for k, v in proofs.most_common(5)],
        "outcomes": [f"{k} ({v})" for k, v in outcomes.most_common(5)],
        "language_cues": [f"{k} ({v})" for k, v in cues.most_common(15)],
    }


# ---------------------------------------------------------------------------
# Ad-library aggregations (from analyzer output, NOT hardcoded categories)
# ---------------------------------------------------------------------------

def _summarize_ad_library(
    ad_library_data: Any,
    ad_creative_patterns: Any,
) -> Dict[str, Any]:
    """Pull the most important per-ad analyzer signals into a flat summary.

    Surfaces fields we currently throw away when populating the Excel template:
    primary_psychological_trigger, emotional_trigger, messaging_angle,
    iterative_suggestions.alternative_hooks. Those are the most strategy-relevant
    outputs of the Vision API analysis.
    """
    ads: List[Dict[str, Any]] = []
    if isinstance(ad_library_data, dict):
        for k in ("ads", "brand_ads", "items", "results"):
            if isinstance(ad_library_data.get(k), list):
                ads = ad_library_data[k]
                break
    elif isinstance(ad_library_data, list):
        ads = ad_library_data

    psych_triggers: Counter = Counter()
    emo_triggers: Counter = Counter()
    angles: Counter = Counter()
    alt_hooks: List[str] = []
    fmt: Counter = Counter()
    framework: Counter = Counter()

    for ad in ads or []:
        if not isinstance(ad, dict):
            continue
        analysis = ad.get("creative_analysis") or {}
        if not isinstance(analysis, dict):
            continue
        if analysis.get("primary_psychological_trigger"):
            psych_triggers[str(analysis["primary_psychological_trigger"]).strip()] += 1
        if analysis.get("emotional_trigger"):
            emo_triggers[str(analysis["emotional_trigger"]).strip()] += 1
        if analysis.get("messaging_angle"):
            angles[str(analysis["messaging_angle"]).strip()] += 1
        if analysis.get("creative_format"):
            fmt[str(analysis["creative_format"]).strip()] += 1
        if analysis.get("framework"):
            framework[str(analysis["framework"]).strip()] += 1
        sugg = analysis.get("iterative_suggestions") or {}
        if isinstance(sugg, dict):
            for h in sugg.get("alternative_hooks") or []:
                if h:
                    alt_hooks.append(str(h).strip())

    summary = {
        "n_ads": len(ads),
        "psych_triggers": [f"{k} ({v})" for k, v in psych_triggers.most_common(5)],
        "emotional_triggers": [f"{k} ({v})" for k, v in emo_triggers.most_common(5)],
        "messaging_angles": [f"{k} ({v})" for k, v in angles.most_common(5)],
        "alternative_hooks_seen": _top_strings(alt_hooks, 8),
        "top_creative_formats": [f"{k} ({v})" for k, v in fmt.most_common(5)],
        "top_frameworks": [f"{k} ({v})" for k, v in framework.most_common(5)],
    }

    if isinstance(ad_creative_patterns, dict):
        # Fold in any pre-computed patterns the orchestrator already generated
        for k, v in ad_creative_patterns.items():
            if k in summary:
                continue
            if isinstance(v, list) and v:
                summary[k] = _top_strings(v, 5)
            elif isinstance(v, str) and v:
                summary[k] = v

    return summary


# ---------------------------------------------------------------------------
# Public entry — build the dict and render the prompt block
# ---------------------------------------------------------------------------

def build_brand_context(
    brand: Any,
    insights_so_far: Optional[Dict[str, Any]] = None,
    snippets: Optional[List[Dict[str, Any]]] = None,
    ad_library_data: Any = None,
    ad_creative_patterns: Any = None,
) -> Dict[str, Any]:
    """Assemble a structured brand_context dict from the data already in hand.

    Every value is sourced from `brand`, `insights_so_far`, `snippets`, or
    ad library — nothing is invented or substituted with defaults.
    """
    insights_so_far = insights_so_far or {}

    def _get(*keys, default=None):
        """Try multiple keys on insights_so_far OR brand attributes in order."""
        for k in keys:
            if isinstance(k, tuple):
                obj, attr = k
                if obj is None:
                    continue
                v = getattr(obj, attr, None)
                if v:
                    return v
            else:
                if k in insights_so_far and insights_so_far[k]:
                    return insights_so_far[k]
        return default

    # Brand DNA (static identity)
    brand_dna = {
        "name": getattr(brand, "name", "") or "",
        "sector": getattr(brand, "sector", "") or "",
        "vertical": getattr(brand, "vertical", "") or "",
        "description": getattr(brand, "description", "") or "",
        "target_audience": getattr(brand, "target_audience", "") or "",
        "products": _top_strings(getattr(brand, "products", None) or [], 5),
        "brand_aesthetic": _top_strings(getattr(brand, "brand_aesthetic", None) or [], 5),
        "brand_values": _top_strings(getattr(brand, "brand_values", None) or [], 5),
        "tone_of_voice": _top_strings(getattr(brand, "tone_of_voice", None) or [], 5),
    }

    # Voice of customer (already-derived insights from earlier pipeline phases)
    voc = {
        "top_pain_points": _top_strings(_get("market_pain_points", "pain_points") or [], 6),
        "top_value_props": _top_strings(_get("value_props") or [], 6),
        "top_desires": _top_strings(_get("customer_desires") or [], 5),
        "top_triggers": _top_strings(_get("purchase_triggers") or [], 5),
        "top_objections": _top_strings(_get("objections") or [], 5),
        "decision_factors": _top_strings(_get("decision_factors") or [], 5),
        "messaging_angles": _top_strings(_get("messaging_angles") or [], 5),
        "verbatim_quotes": _top_strings(_get("verbatim_quotes") or [], 4),
        "customer_language": _top_strings(_get("customer_language") or [], 12),
        "tone_emotions": _top_strings(_get("tone_emotions") or [], 6),
        "trending_topics": _top_strings(_get("trending_topics") or [], 6),
        "price_sensitivity": _stringify(_get("price_sensitivity")),
    }

    # Per-source voice + intake distributions (only if we have raw snippets)
    per_source = per_source_voice(snippets or [])
    intake = _aggregate_tag_distributions(snippets or [])

    # Competitor framing
    ca = _get("competitor_analysis") or {}
    competitors = {
        "differentiation": _top_strings(
            (ca.get("brand_differentiation") if isinstance(ca, dict) else None)
            or (ca.get("differentiation") if isinstance(ca, dict) else None)
            or [],
            5,
        ),
        "competitive_position": _stringify(
            ca.get("positioning") if isinstance(ca, dict) else None
        ),
        "named_competitors": _top_strings(_get("competitors_mentioned") or [], 5),
    }

    # Ad library (analyzer output)
    ad_summary = _summarize_ad_library(ad_library_data, ad_creative_patterns)

    return {
        "brand_dna": brand_dna,
        "voc": voc,
        "per_source": per_source,
        "intake": intake,
        "competitors": competitors,
        "ad_summary": ad_summary,
    }


# ---------------------------------------------------------------------------
# Discovery corpus — the FULL package handed to the LLM for archetype discovery
# ---------------------------------------------------------------------------

def _enumerate_snippets(snippets: List[Dict[str, Any]], max_snippets: int = 250,
                        per_source_cap_fraction: float = 0.40) -> List[Dict[str, Any]]:
    """Pick up to max_snippets, balanced across sources, ranked by stance_confidence."""
    if not snippets:
        return []
    if len(snippets) <= max_snippets:
        ranked = sorted(snippets, key=lambda s: -(s.get("stance_confidence") or 0))
        return list(enumerate(ranked))  # type: ignore

    per_source_cap = max(5, int(max_snippets * per_source_cap_fraction))
    by_source: Dict[str, List[Dict[str, Any]]] = {}
    for s in sorted(snippets, key=lambda s: -(s.get("stance_confidence") or 0)):
        by_source.setdefault(s.get("source_type") or "unknown", []).append(s)

    selected: List[Dict[str, Any]] = []
    consumed: Dict[str, int] = {src: 0 for src in by_source}
    while len(selected) < max_snippets:
        progress = False
        for src in sorted(by_source.keys(), key=lambda k: -len(by_source[k])):
            if consumed[src] >= per_source_cap or not by_source[src]:
                continue
            selected.append(by_source[src].pop(0))
            consumed[src] += 1
            progress = True
            if len(selected) >= max_snippets:
                break
        if not progress:
            for src in by_source:
                while by_source[src] and len(selected) < max_snippets:
                    selected.append(by_source[src].pop(0))
            break
    return list(enumerate(selected))  # type: ignore


def render_snippets_block(enumerated: List[Any], max_chars_per_snippet: int = 320) -> str:
    """Render snippets with their full metadata so the discovery LLM can reason about each.

    Each line: [INDEX] (source, stance, conf, trigger, blocker) "content"
    The discovery prompt will reference snippets by INDEX in its archetype output.
    """
    lines: List[str] = []
    for idx, s in enumerated:
        src = s.get("source_type") or "?"
        stance = s.get("general_stance") or "?"
        conf = s.get("stance_confidence")
        conf_str = f"{conf:.2f}" if conf is not None else "?"
        trig = s.get("primary_trigger") or ""
        block = s.get("blocker_type") or ""
        outc = s.get("desired_outcome_level") or ""
        proof = s.get("proof_type_trusted") or ""
        cues = s.get("language_cues") or []
        cue_str = ",".join(cues[:3]) if isinstance(cues, list) else ""

        meta_parts = [f"src={src}", f"stance={stance}", f"conf={conf_str}"]
        if trig: meta_parts.append(f"trigger={trig}")
        if block: meta_parts.append(f"blocker={block}")
        if outc: meta_parts.append(f"outcome={outc}")
        if proof: meta_parts.append(f"proof={proof}")
        if cue_str: meta_parts.append(f"cues={cue_str}")

        content = (s.get("content") or "").replace("\n", " ").strip()
        if len(content) > max_chars_per_snippet:
            content = content[:max_chars_per_snippet - 3] + "..."

        lines.append(f"[{idx}] ({', '.join(meta_parts)}) \"{content}\"")
    return "\n".join(lines)


def render_ads_block(ad_library_data: Any, max_ads: int = 60,
                     max_chars_per_ad: int = 400) -> str:
    """Render the FULL per-ad analyzer output (not aggregated) so the LLM can
    cross-reference ad creative with VoC archetypes.

    Surfaces fields the export currently throws away: psychological_trigger,
    emotional_trigger, messaging_angle, primary_persona, scene_breakdown summary.
    """
    ads: List[Dict[str, Any]] = []
    if isinstance(ad_library_data, dict):
        for k in ("ads", "brand_ads", "items", "results"):
            if isinstance(ad_library_data.get(k), list):
                ads = ad_library_data[k]
                break
    elif isinstance(ad_library_data, list):
        ads = ad_library_data
    if not ads:
        return "(no ad library data)"

    lines: List[str] = []
    for i, ad in enumerate(ads[:max_ads]):
        if not isinstance(ad, dict):
            continue
        analysis = ad.get("creative_analysis") or {}
        if not isinstance(analysis, dict):
            continue
        bits = []
        for key in ("framework", "creative_format", "visual_type", "talent_type",
                    "primary_psychological_trigger", "emotional_trigger",
                    "messaging_angle", "awareness_level", "hook_type",
                    "first_frame_element", "tone", "primary_persona"):
            v = analysis.get(key)
            if v:
                bits.append(f"{key}={str(v)[:60]}")
        body = (ad.get("ad_body") or analysis.get("script_summary") or "")[:max_chars_per_ad]
        body = str(body).replace("\n", " ").strip()
        lines.append(f"[AD#{i}] {' | '.join(bits)} :: \"{body}\"")
    return "\n".join(lines) if lines else "(no analyzed ads)"


def build_discovery_corpus(
    brand: Any,
    insights_so_far: Optional[Dict[str, Any]] = None,
    snippets: Optional[List[Dict[str, Any]]] = None,
    ad_library_data: Any = None,
    ad_creative_patterns: Any = None,
    max_snippets: int = 220,
    max_ads: int = 50,
) -> Dict[str, Any]:
    """Assemble the full data package for archetype discovery.

    Returns a dict with rendered text blocks ready to drop into a prompt:
      - brand_block:    structured brand+VoC summary (build_brand_context render)
      - snippets_block: enumerated snippets with all metadata
      - ads_block:      per-ad analyzer output (full, not aggregated)
      - meta:           {snippet_count, ad_count, source_distribution}

    The discovery LLM receives these together and discovers archetypes as
    they emerge from the data — no predefined taxonomy.
    """
    ctx = build_brand_context(
        brand=brand,
        insights_so_far=insights_so_far,
        snippets=snippets,
        ad_library_data=ad_library_data,
        ad_creative_patterns=ad_creative_patterns,
    )
    brand_block = render_context_block(ctx)

    enumerated = _enumerate_snippets(snippets or [], max_snippets=max_snippets)
    snippets_block = render_snippets_block(enumerated)

    ads_block = render_ads_block(ad_library_data, max_ads=max_ads)

    source_dist: Counter = Counter()
    for _, s in enumerated:
        source_dist[s.get("source_type") or "unknown"] += 1

    return {
        "brand_block": brand_block,
        "snippets_block": snippets_block,
        "ads_block": ads_block,
        "enumerated_snippets": enumerated,  # for downstream: index -> snippet lookup
        "meta": {
            "snippet_count": len(enumerated),
            "ad_count": ads_block.count("[AD#"),
            "source_distribution": dict(source_dist),
            "approx_input_chars": len(brand_block) + len(snippets_block) + len(ads_block),
        },
    }


def render_context_block(ctx: Dict[str, Any]) -> str:
    """Render the brand_context dict into a prompt-ready text block.

    Sections that are empty for this brand are omitted entirely so the prompt
    doesn't get padded with placeholders that confuse the LLM.
    """
    if not ctx:
        return "(no brand context available)"

    lines: List[str] = []

    dna = ctx.get("brand_dna") or {}
    name = dna.get("name") or "this brand"
    cat = " / ".join([x for x in [dna.get("sector"), dna.get("vertical")] if x])
    lines.append(f"# BRAND CONTEXT — {name}" + (f" ({cat})" if cat else ""))
    if dna.get("description"):
        lines.append(f"What it does: {dna['description']}")
    if dna.get("target_audience"):
        lines.append(f"Self-described audience: {dna['target_audience']}")
    if dna.get("products"):
        lines.append(f"Products: {', '.join(dna['products'])}")
    if dna.get("brand_aesthetic"):
        lines.append(f"Aesthetic: {', '.join(dna['brand_aesthetic'])}")
    if dna.get("brand_values"):
        lines.append(f"Stated values: {', '.join(dna['brand_values'])}")
    if dna.get("tone_of_voice"):
        lines.append(f"Brand tone: {', '.join(dna['tone_of_voice'])}")

    voc = ctx.get("voc") or {}
    if any(voc.get(k) for k in ("top_pain_points", "top_desires", "top_triggers",
                                "top_objections", "messaging_angles", "verbatim_quotes")):
        lines.append("\n## VOICE OF CUSTOMER (from already-classified VoC corpus)")
        if voc.get("top_pain_points"):
            lines.append("Pain points heard:")
            lines.append(_bullet(voc["top_pain_points"]))
        if voc.get("top_desires"):
            lines.append("Customer desires heard:")
            lines.append(_bullet(voc["top_desires"]))
        if voc.get("top_triggers"):
            lines.append("Purchase triggers heard:")
            lines.append(_bullet(voc["top_triggers"]))
        if voc.get("top_objections"):
            lines.append("Objections heard:")
            lines.append(_bullet(voc["top_objections"]))
        if voc.get("decision_factors"):
            lines.append("Decision factors heard:")
            lines.append(_bullet(voc["decision_factors"]))
        if voc.get("messaging_angles"):
            lines.append("Messaging angles already used:")
            lines.append(_bullet(voc["messaging_angles"]))
        if voc.get("top_value_props"):
            lines.append("Value props the brand emphasizes:")
            lines.append(_bullet(voc["top_value_props"]))
        if voc.get("tone_emotions"):
            lines.append(f"Dominant tones/emotions: {', '.join(voc['tone_emotions'])}")
        if voc.get("trending_topics"):
            lines.append(f"Trending topics: {', '.join(voc['trending_topics'])}")
        if voc.get("customer_language"):
            lines.append(f"Customer vocabulary (verbatim cues): {', '.join(voc['customer_language'])}")
        if voc.get("price_sensitivity"):
            lines.append(f"Price sensitivity signal: {voc['price_sensitivity']}")
        if voc.get("verbatim_quotes"):
            lines.append("Representative verbatim quotes:")
            for q in voc["verbatim_quotes"]:
                lines.append(f"  > \"{q}\"")

    per_source = ctx.get("per_source") or []
    if per_source:
        lines.append("\n## PER-SOURCE VOICE (each source attracts a different mindset)")
        for entry in per_source:
            src = entry.get("source_type", "?")
            n = entry.get("count", 0)
            samples = entry.get("samples") or []
            lines.append(f"  [{src}, n={n}]")
            for s in samples:
                lines.append(f"    > \"{s}\"")

    intake = ctx.get("intake") or {}
    if any(intake.get(k) for k in ("triggers", "blockers", "proof_types", "outcomes", "language_cues")):
        lines.append("\n## INTAKE ENGINE TAG DISTRIBUTIONS (per-snippet classifications)")
        if intake.get("triggers"):
            lines.append(f"Top primary triggers: {', '.join(intake['triggers'])}")
        if intake.get("blockers"):
            lines.append(f"Top blockers: {', '.join(intake['blockers'])}")
        if intake.get("proof_types"):
            lines.append(f"Proof types trusted: {', '.join(intake['proof_types'])}")
        if intake.get("outcomes"):
            lines.append(f"Desired outcome levels: {', '.join(intake['outcomes'])}")
        if intake.get("language_cues"):
            lines.append(f"Language cues: {', '.join(intake['language_cues'])}")

    comp = ctx.get("competitors") or {}
    if comp.get("differentiation") or comp.get("competitive_position") or comp.get("named_competitors"):
        lines.append("\n## COMPETITIVE FRAMING")
        if comp.get("competitive_position"):
            lines.append(f"Position: {comp['competitive_position']}")
        if comp.get("differentiation"):
            lines.append(f"Differentiation: {', '.join(comp['differentiation'])}")
        if comp.get("named_competitors"):
            lines.append(f"Mentioned competitors: {', '.join(comp['named_competitors'])}")

    ad = ctx.get("ad_summary") or {}
    if ad.get("n_ads"):
        lines.append(f"\n## AD-LIBRARY OBSERVATIONS (from {ad['n_ads']} analyzed ads)")
        if ad.get("psych_triggers"):
            lines.append(f"Primary psychological triggers used: {', '.join(ad['psych_triggers'])}")
        if ad.get("emotional_triggers"):
            lines.append(f"Emotional triggers used: {', '.join(ad['emotional_triggers'])}")
        if ad.get("messaging_angles"):
            lines.append(f"Ad messaging angles: {', '.join(ad['messaging_angles'])}")
        if ad.get("top_frameworks"):
            lines.append(f"Frameworks observed: {', '.join(ad['top_frameworks'])}")
        if ad.get("top_creative_formats"):
            lines.append(f"Creative formats: {', '.join(ad['top_creative_formats'])}")
        if ad.get("alternative_hooks_seen"):
            lines.append("Hook ideas surfaced by the analyzer:")
            lines.append(_bullet(ad["alternative_hooks_seen"]))

    return "\n".join(lines)
