# -*- coding: utf-8 -*-
"""
Brand Intelligence Export Service.
Generates comprehensive markdown exports from Brand + Insight objects.
Used by both the CLI (export_brand.py) and the API endpoint.
"""
from datetime import datetime
from typing import Any


# ── Formatting helpers ─────────────────────────────────────────────────────

def fmt_list(items, bullet="-"):
    if not items:
        return f"{bullet} (no data)\n"
    out = []
    for item in items:
        if isinstance(item, dict):
            out.append(f"{bullet} {item.get('text', item.get('name', str(item)))}")
        else:
            out.append(f"{bullet} {item}")
    return "\n".join(out) + "\n"


def fmt_icps(icps):
    if not icps:
        return "(no ICPs identified)\n"
    out = []
    for i, icp in enumerate(icps, 1):
        if isinstance(icp, dict):
            name = icp.get('name', f'Persona {i}')
            desc = icp.get('description', '')
            age = icp.get('age_range', 'N/A')
            chars = icp.get('characteristics', [])
            pains = icp.get('pain_points', [])
            motivs = icp.get('motivations', [])
            out.append(f"### {i}. {name}\n")
            if desc:
                out.append(f"{desc}\n")
            out.append(f"- **Age Range**: {age}")
            if chars:
                out.append(f"- **Characteristics**: {', '.join(chars) if isinstance(chars, list) else chars}")
            if pains:
                out.append(f"- **Pain Points**: {', '.join(pains) if isinstance(pains, list) else pains}")
            if motivs:
                out.append(f"- **Motivations**: {', '.join(motivs) if isinstance(motivs, list) else motivs}")
            out.append("")
        else:
            out.append(f"- {icp}")
    return "\n".join(out) + "\n"


def fmt_angles(angles):
    if not angles:
        return "(no messaging angles identified)\n"
    out = []
    for i, a in enumerate(angles, 1):
        if isinstance(a, dict):
            name = a.get('name', f'Angle {i}')
            hook = a.get('hook', '')
            desc = a.get('description', '')
            evidence = a.get('supporting_evidence', '')
            out.append(f"### {i}. {name}\n")
            if hook:
                out.append(f'> **Hook**: "{hook}"\n')
            if desc:
                out.append(f"{desc}\n")
            if evidence:
                out.append(f"**Evidence**: {evidence}\n")
        else:
            out.append(f"- {a}")
    return "\n".join(out) + "\n"


def fmt_objections(objections):
    if not objections:
        return "- (none identified)\n"
    out = []
    for obj in objections:
        if isinstance(obj, dict):
            text = obj.get('objection', str(obj))
            freq = obj.get('frequency', '')
            counter = obj.get('counter_messaging', '')
            out.append(f"- **{text}**")
            if freq:
                out.append(f"  - Frequency: {freq}")
            if counter:
                out.append(f"  - Counter-messaging: {counter}")
        else:
            out.append(f"- {obj}")
    return "\n".join(out) + "\n"


def fmt_verbatims(quotes):
    if not quotes:
        return "(no verbatim quotes collected)\n"
    out = []
    for q in quotes:
        if isinstance(q, dict):
            quote = q.get('quote', str(q))
            context = q.get('context', '')
            use = q.get('use_case', '')
            out.append(f'> "{quote}"')
            if context:
                out.append(f"> *Context: {context}*")
            if use:
                out.append(f"> *Use case: {use}*")
            out.append("")
        else:
            out.append(f'> "{q}"\n')
    return "\n".join(out) + "\n"


def fmt_hooks_library(hooks):
    if not hooks or not isinstance(hooks, dict):
        return "(no hooks library)\n"
    out = []
    for category, items in hooks.items():
        if not items:
            continue
        out.append(f"### {category.replace('_', ' ').title()}\n")
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    hook_text = item.get('hook', item.get('text', str(item)))
                    persona = item.get('target_persona', item.get('persona', ''))
                    out.append(f'- "{hook_text}"')
                    if persona:
                        out.append(f"  - Target: {persona}")
                else:
                    out.append(f"- {item}")
        elif isinstance(items, dict):
            for k, v in items.items():
                out.append(f"- **{k}**: {v}")
        else:
            out.append(f"- {items}")
        out.append("")
    return "\n".join(out) + "\n"


def fmt_competitor_profiles(profiles):
    if not profiles:
        return "(no competitor profiles)\n"
    out = []
    for i, cp in enumerate(profiles, 1):
        if isinstance(cp, dict):
            name = cp.get('name', cp.get('competitor', f'Competitor {i}'))
            out.append(f"### {i}. {name}\n")
            for k, v in cp.items():
                if k in ('name', 'competitor'):
                    continue
                label = k.replace('_', ' ').title()
                if isinstance(v, list):
                    out.append(f"- **{label}**: {', '.join(str(x) for x in v)}")
                elif isinstance(v, dict):
                    out.append(f"- **{label}**:")
                    for sk, sv in v.items():
                        out.append(f"  - {sk}: {sv}")
                else:
                    out.append(f"- **{label}**: {v}")
            out.append("")
        else:
            out.append(f"- {cp}")
    return "\n".join(out) + "\n"


def fmt_swot(swot):
    if not swot or not isinstance(swot, dict):
        return "(no SWOT analysis)\n"
    out = []
    for section in ['strengths', 'weaknesses', 'opportunities', 'threats']:
        items = swot.get(section, [])
        out.append(f"### {section.title()}\n")
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    point = item.get('point', item.get('name', str(item)))
                    evidence = item.get('evidence', '')
                    action = (item.get('leverage_how', '') or item.get('mitigate_how', '') or
                              item.get('capture_how', '') or item.get('defend_how', ''))
                    out.append(f"- **{point}**")
                    if evidence:
                        out.append(f"  - Evidence: {evidence}")
                    if action:
                        out.append(f"  - Action: {action}")
                else:
                    out.append(f"- {item}")
        elif items:
            out.append(f"- {items}")
        else:
            out.append("- (none)")
        out.append("")
    summary = swot.get('summary', swot.get('analysis', ''))
    if summary:
        out.append(f"**Summary**: {summary}\n")
    return "\n".join(out) + "\n"


def fmt_competitive_matrix(matrix):
    if not matrix or not isinstance(matrix, dict):
        return "(no competitive matrix)\n"
    out = []
    dimensions = matrix.get('comparison_dimensions', [])
    if dimensions and isinstance(dimensions, list):
        out.append("### Dimension Comparison\n")
        for dim in dimensions:
            if isinstance(dim, dict):
                name = dim.get('dimension', 'Unknown')
                our = dim.get('our_brand', '')
                comps = dim.get('competitors', {})
                out.append(f"**{name}**:")
                if our:
                    out.append(f"- *Our brand*: {our}")
                if isinstance(comps, dict):
                    for comp_name, comp_val in comps.items():
                        out.append(f"- *{comp_name}*: {comp_val}")
                out.append("")
            else:
                out.append(f"- {dim}")
    for field in ['our_strengths', 'our_weaknesses', 'opportunities', 'threats']:
        items = matrix.get(field, [])
        if items:
            label = field.replace('_', ' ').title()
            out.append(f"**{label}**:")
            if isinstance(items, list):
                for item in items:
                    out.append(f"- {item}")
            else:
                out.append(f"- {items}")
            out.append("")
    for field in ['positioning_recommendation', 'messaging_differentiation']:
        val = matrix.get(field)
        if val:
            label = field.replace('_', ' ').title()
            if isinstance(val, list):
                out.append(f"**{label}**:")
                for item in val:
                    out.append(f"- {item}")
            else:
                out.append(f"**{label}**: {val}")
            out.append("")
    return "\n".join(out) + "\n"


def fmt_cross_source(insights):
    if not insights or not isinstance(insights, dict):
        return "(no cross-source insights)\n"
    out = []
    for k, v in insights.items():
        label = k.replace('_', ' ').title()
        if isinstance(v, list) and v:
            out.append(f"### {label}\n")
            for item in v:
                if isinstance(item, dict):
                    main_key = (item.get('pain_point') or item.get('praise_type') or
                                item.get('theme') or item.get('objection') or
                                item.get('name', ''))
                    sources = item.get('validated_by', item.get('sources', []))
                    count = item.get('source_count', len(sources) if isinstance(sources, list) else '')
                    if main_key:
                        source_str = ', '.join(sources) if isinstance(sources, list) else str(sources)
                        out.append(f"- **{main_key}** — {count} sources ({source_str})")
                    else:
                        out.append(f"- {item}")
                else:
                    out.append(f"- {item}")
            out.append("")
        elif isinstance(v, dict) and v:
            out.append(f"### {label}\n")
            for sk, sv in v.items():
                if isinstance(sv, dict):
                    pct_pos = sv.get('positive_pct', '')
                    pct_neg = sv.get('negative_pct', '')
                    total = sv.get('total', '')
                    if pct_pos != '' or total:
                        out.append(f"- **{sk}**: {total} items — {pct_pos:.0f}% positive, {pct_neg:.0f}% negative")
                    else:
                        out.append(f"- **{sk}**: {sv}")
                else:
                    out.append(f"- **{sk}**: {sv}")
            out.append("")
        elif v:
            out.append(f"### {label}\n{v}\n")
    return "\n".join(out) + "\n"


def fmt_products(products):
    if not products:
        return "- (no products listed)\n"
    out = []
    for p in products:
        if isinstance(p, dict):
            name = p.get('name', 'Unknown')
            desc = p.get('description', '')
            price = p.get('price', '')
            line = f"- **{name}**"
            if price:
                line += f" ({price})"
            if desc:
                line += f": {desc}"
            out.append(line)
        else:
            out.append(f"- {p}")
    return "\n".join(out) + "\n"


def fmt_tiktok_trends(trends):
    if not trends or not isinstance(trends, dict):
        return "(no TikTok trends data)\n"
    out = []
    for k, v in trends.items():
        label = k.replace('_', ' ').title()
        if isinstance(v, list):
            out.append(f"### {label}\n")
            for item in v:
                if isinstance(item, dict):
                    out.append(f"- {item.get('name', item.get('text', str(item)))}")
                else:
                    out.append(f"- {item}")
            out.append("")
        elif isinstance(v, dict):
            out.append(f"### {label}\n")
            for sk, sv in v.items():
                out.append(f"- **{sk}**: {sv}")
            out.append("")
        elif v:
            out.append(f"**{label}**: {v}\n")
    return "\n".join(out) + "\n"


def fmt_top_quotes(quotes):
    if not quotes:
        return "(no top quotes)\n"
    out = []
    for i, q in enumerate(quotes, 1):
        if isinstance(q, dict):
            text = q.get('quote', q.get('text', q.get('content', str(q))))
            source = q.get('source', q.get('source_type', ''))
            sentiment = q.get('sentiment', '')
            out.append(f'{i}. > "{text}"')
            tags = []
            if source:
                tags.append(source)
            if sentiment:
                tags.append(sentiment)
            if tags:
                out.append(f"   *— {', '.join(tags)}*")
            out.append("")
        else:
            out.append(f'{i}. > "{q}"\n')
    return "\n".join(out) + "\n"


def fmt_recommended_hooks(hooks):
    if not hooks:
        return "(no recommended hooks)\n"
    out = []
    for h in hooks:
        if isinstance(h, dict):
            htype = h.get('type', 'General').upper()
            text = h.get('hook', h.get('text', str(h)))
            persona = h.get('target_persona', '')
            reasoning = h.get('reasoning', '')
            out.append(f'**{htype}**: "{text}"')
            if persona:
                out.append(f"- Target persona: {persona}")
            if reasoning:
                out.append(f"- Reasoning: {reasoning}")
            out.append("")
        else:
            out.append(f'- "{h}"')
    return "\n".join(out) + "\n"


# ── Main export builder ───────────────────────────────────────────────────

def build_export(brand: Any, insight: Any) -> str:
    """Build the comprehensive markdown export from Brand + Insight ORM objects."""
    b = brand
    ins = insight

    md = f"""# {b.name} — Brand Intelligence Report

*Exported: {datetime.now().strftime('%Y-%m-%d %H:%M')}*

---

## 1. Brand DNA

| Field | Value |
|-------|-------|
| **Name** | {b.name} |
| **Website** | {b.website_url or 'N/A'} |
| **Sector** | {b.sector or 'N/A'} |
| **Vertical** | {b.vertical or 'N/A'} |
| **Tagline** | {b.tagline or 'N/A'} |
| **Target Audience** | {b.target_audience or 'N/A'} |

"""
    if b.brand_values:
        md += f"**Brand Values**: {', '.join(b.brand_values) if isinstance(b.brand_values, list) else b.brand_values}\n\n"
    if b.brand_aesthetic:
        md += f"**Aesthetic**: {', '.join(b.brand_aesthetic) if isinstance(b.brand_aesthetic, list) else b.brand_aesthetic}\n\n"
    if b.tone_of_voice:
        md += f"**Tone of Voice**: {', '.join(b.tone_of_voice) if isinstance(b.tone_of_voice, list) else b.tone_of_voice}\n\n"
    if b.brand_colors:
        md += f"**Colors**: {', '.join(b.brand_colors) if isinstance(b.brand_colors, list) else b.brand_colors}\n\n"
    if b.fonts:
        md += f"**Fonts**: {', '.join(b.fonts) if isinstance(b.fonts, list) else b.fonts}\n\n"

    md += "### Products & Services\n\n"
    md += fmt_products(b.products or b.product_descriptions)

    if b.description:
        md += f"\n### Description\n\n{b.description}\n"

    md += f"""
---

## 2. Brand Summary

{ins.brand_summary or '(no summary)'}

- **Sentiment Score**: {ins.sentiment_score or 'N/A'} / 5
- **Total Data Points**: {ins.total_mentions or 'N/A'}

"""

    md += """---

## 3. Creative Target Personas (ICPs)

"""
    md += fmt_icps(ins.icps)

    md += """---

## 4. Brand Perception

### What People Love
"""
    md += fmt_list(ins.top_positives)
    md += """
### Common Concerns
"""
    md += fmt_list(ins.top_negatives)
    md += """
### Competitors Mentioned
"""
    md += fmt_list(ins.competitors_mentioned)

    md += """
---

## 5. Market & Segment Research

### Market Pain Points
"""
    md += fmt_list(ins.market_pain_points)
    md += """
### Customer Language (Verbatims)
"""
    if ins.customer_language:
        for item in ins.customer_language:
            md += f'- "{item}"\n'
    else:
        md += "- (no data)\n"
    md += """
### Customer Desires
"""
    md += fmt_list(ins.customer_desires)
    md += """
### Trending Topics
"""
    md += fmt_list(ins.trending_topics)

    md += """
---

## 6. Purchase Psychology

### Purchase Triggers
"""
    md += fmt_list(ins.purchase_triggers)
    md += """
### Objections & Counter-Messaging
"""
    md += fmt_objections(ins.objections)
    md += """
### Decision Factors (Ranked)
"""
    if ins.decision_factors:
        for i, item in enumerate(ins.decision_factors, 1):
            md += f"{i}. {item}\n"
    else:
        md += "- (no data)\n"
    md += "\n"

    md += "### Price Sensitivity\n\n"
    price = ins.price_sensitivity
    if price and isinstance(price, dict):
        md += f"- **Overall Sensitivity**: {price.get('overall_sensitivity', 'N/A')}\n"
        md += f"- **Value Perception**: {price.get('value_perception', 'N/A')}\n"
        complaints = price.get('price_complaints', [])
        if complaints:
            md += f"- **Price Complaints**: {', '.join(complaints) if isinstance(complaints, list) else complaints}\n"
    else:
        md += "- (no data)\n"

    md += """
---

## 7. Competitive Intelligence

### Competitor Profiles
"""
    md += fmt_competitor_profiles(ins.competitor_profiles)

    comp = ins.competitor_analysis
    if comp and isinstance(comp, dict):
        md += "### Competitive Overview\n\n"
        main_comp = comp.get('main_competitors', [])
        if main_comp:
            md += f"**Main Competitors**: {', '.join(main_comp)}\n\n"
        our_adv = comp.get('our_advantages', [])
        if our_adv:
            md += "**Our Advantages**:\n"
            for item in our_adv:
                md += f"- {item}\n"
            md += "\n"
        their_adv = comp.get('their_advantages', [])
        if their_adv:
            md += "**Their Advantages**:\n"
            for item in their_adv:
                md += f"- {item}\n"
            md += "\n"
        positioning = comp.get('positioning_opportunity', '')
        if positioning:
            md += f"**Positioning Opportunity**: {positioning}\n\n"

    md += "### SWOT Analysis\n\n"
    md += fmt_swot(ins.swot_analysis)

    md += "### Competitive Matrix\n\n"
    md += fmt_competitive_matrix(ins.competitive_matrix)

    md += """
---

## 8. Messaging Angles

"""
    md += fmt_angles(ins.messaging_angles)

    md += """---

## 9. Hooks Library

"""
    md += fmt_hooks_library(ins.hooks_library)

    md += """---

## 10. Recommended Hooks

"""
    md += fmt_recommended_hooks(ins.recommended_hooks)

    md += """---

## 11. Pain Points & Value Propositions

### Pain Points (for Ad Messaging)
"""
    md += fmt_list(ins.pain_points)
    md += """
### Value Propositions (to Highlight)
"""
    md += fmt_list(ins.value_props)

    md += """
---

## 12. Tone & Emotional Journey

"""
    md += fmt_list(ins.tone_emotions)

    md += """
---

## 13. Verbatim Quotes (for Ads)

"""
    md += fmt_verbatims(ins.verbatim_quotes)

    md += """---

## 14. Top Quotes from Reviews & Social

"""
    md += fmt_top_quotes(ins.top_quotes)

    md += """---

## 15. Cross-Source Insights

"""
    md += fmt_cross_source(ins.cross_source_insights)

    md += """---

## 16. Content Opportunities & Feature Requests

### Content Opportunities
"""
    md += fmt_list(ins.content_opportunities)
    md += """
### Feature Requests
"""
    md += fmt_list(ins.feature_requests)

    if ins.tiktok_trends:
        md += """
---

## 17. TikTok Trends

"""
        md += fmt_tiktok_trends(ins.tiktok_trends)

    md += """
---

## 18. Data Summary

"""
    ds = ins.data_summary
    if ds and isinstance(ds, dict):
        by_source = ds.get('by_source', {})
        if by_source:
            md += "| Source | Items |\n|--------|-------|\n"
            for src, count in by_source.items():
                md += f"| {src.title()} | {count} |\n"
            md += "\n"
        by_type = ds.get('by_mention_type', {})
        if by_type:
            md += "| Mention Type | Items |\n|-------------|-------|\n"
            for mt, count in by_type.items():
                md += f"| {mt.replace('_', ' ').title()} | {count} |\n"
            md += "\n"
        for k, v in ds.items():
            if k not in ('by_source', 'by_mention_type') and v:
                md += f"- **{k.replace('_', ' ').title()}**: {v}\n"
    else:
        md += "- (no data summary)\n"

    md += f"""
---

*Generated by Brand Intelligence Scraper*
*Export date: {datetime.now().strftime('%Y-%m-%d %H:%M')}*
"""

    return md
