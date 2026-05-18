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
        # Skip metadata keys that aren't hook categories
        if category in ('brand', 'total_hooks', 'total'):
            continue
        out.append(f"### {category.replace('_', ' ').title()}\n")
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    hook_text = item.get('hook_text', item.get('hook', item.get('text', '')))
                    if not hook_text:
                        continue
                    hook_type = item.get('hook_type', '')
                    persona = item.get('target_persona', item.get('persona', ''))
                    pain = item.get('pain_point_addressed', '')
                    verbatim = item.get('verbatim_source', '')
                    strength = item.get('strength_score', '')
                    platform = item.get('platform_fit', [])

                    type_str = f" [{hook_type}]" if hook_type else ""
                    score_str = f" (strength: {strength}/5)" if strength else ""
                    out.append(f'- **"{hook_text}"**{type_str}{score_str}')
                    if persona:
                        out.append(f"  - Target: {persona}")
                    if pain:
                        out.append(f"  - Pain point: {pain}")
                    if verbatim:
                        out.append(f'  - Based on: "{verbatim}"')
                    if platform and isinstance(platform, list):
                        out.append(f"  - Platforms: {', '.join(platform)}")
                else:
                    out.append(f"- {item}")
        elif isinstance(items, (int, str)):
            out.append(f"- {items}")
        elif isinstance(items, dict):
            for k, v in items.items():
                out.append(f"- **{k}**: {v}")
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

def build_export(brand: Any, insight: Any, scraped_data: list = None) -> str:
    """Build the comprehensive markdown export from Brand + Insight + ScrapedData ORM objects."""
    b = brand
    ins = insight
    raw_data = scraped_data or []

    # ── Build sector/vertical context for system prompt ────────────────
    sector_hint = b.sector or b.vertical or "its market"

    md = f"""# {b.name} — Brand Intelligence Report

*Exported: {datetime.now().strftime('%Y-%m-%d %H:%M')}*

---

## System Instructions

You are a senior creative strategist specialized in {sector_hint}. You have access to a complete brand intelligence report for **{b.name}** ({b.website_url or 'N/A'}) — built from real customer data, ad library analysis, competitor intelligence, and audience research.

### How to use this data

- **Always ground your answers in the data below.** Cite sources when possible: [reddit], [trustpilot], [tiktok], [app_store], [ad_library], [competitor_ads], etc.
- **Use exact customer quotes** when they strengthen the argument. This report contains real verbatims — use them.
- **Reference CTPs by name** (e.g. "Burned and Double-Checking Everything") when discussing audience segments.
- **Reference Target Personas by name** when discussing TOFU / acquisition strategies.
- **Cross-reference sections.** The best insights come from connecting ads (Section 17c) with customer pain points (Section 19b), or competitor gaps (Section 17d) with our weak signals (Section 25).

### What you CAN do beyond this report

- **Search the internet** for updated information: competitor launches, new ads, recent reviews, trending content, pricing changes, market news. This report is a snapshot — the market moves.
- **Visit the brand's website** ({b.website_url or 'N/A'}) and competitors' sites to check current offers, landing pages, pricing, and messaging.
- **Check the Meta Ad Library** for the latest active ads from {b.name} and its competitors.
- **Look up recent TikTok/Instagram content** in the brand's niche for trending formats, sounds, and hooks.
- **Cross-reference with industry benchmarks** (CPM, CTR, CPA ranges) when asked about media buying or performance.

### What you should NOT do

- Do not invent data, quotes, or statistics that aren't in this report or verifiable online.
- Do not present hypotheses as facts. When something is your inference, flag it.
- Do not ignore the CTPs and default to generic "millennials who care about X" personas. The CTPs below are built from real data — use them.

### Report structure quick reference

| Section | What's in it |
|---------|-------------|
| 1-2 | Brand DNA, summary, sentiment |
| 3-6 | ICPs, perception, market research, purchase psychology |
| 7 | Competitive intelligence (SWOT, matrix, profiles) |
| 8-10 | Messaging angles, hooks library, recommended hooks |
| 11-16 | Pain points, tone, quotes, cross-source insights, content ops |
| 17 | TikTok trends |
| 17b-17f | **Ad intelligence**: creative patterns, per-ad analysis, competitor ads, data by topic |
| 18-19 | Data summary, Proto-ICPs |
| 19b-19f | **CTPs, hypothesis layer, target personas, community dialect** |
| 20-21 | Raw verbatims by source, sentiment distribution |
| 22-25 | Angle bank, failed solutions, transformation angles, weak signals |
| 26-30 | UGC briefs, funnel strategy, survey, A/B tests, thumbnails |

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

## 13. Verbatim Quotes (Brand Mentions)

These are real customer quotes about the brand — from reviews, Reddit, forums, and social media. Use for ad copy, testimonials, and persona building.

"""
    md += fmt_verbatims(ins.verbatim_quotes)

    # Extract additional verbatims directly from scraped_data (brand mentions only)
    BRAND_SOURCES = {'reddit', 'trustpilot', 'app_store', 'play_store', 'google_reviews',
                     'g2', 'capterra', 'other_review', 'forum', 'quora', 'youtube_comment',
                     'brand_website', 'competitor_comparison'}
    if raw_data:
        brand_verbatims = []
        for item in raw_data:
            st = getattr(item, 'source_type', '') or ''
            track = getattr(item, 'track', None)
            content = (getattr(item, 'content', '') or '').strip()
            if not content or len(content) < 30:
                continue
            if st.lower() not in BRAND_SOURCES and track != 1:
                continue
            score = getattr(item, 'sentiment_score', None)
            brand_verbatims.append((item, abs(float(score)) if score is not None else 0))

        # Sort by strongest sentiment (most opinionated = most useful for ads)
        brand_verbatims.sort(key=lambda x: x[1], reverse=True)

        shown = brand_verbatims[:30]
        if shown:
            md += "\n### Top Verbatims from Scraped Data (by sentiment strength)\n\n"
            for item, _ in shown:
                content = (getattr(item, 'content', '') or '')[:400].replace('\n', ' ').strip()
                source_type = getattr(item, 'source_type', '') or ''
                source_url = getattr(item, 'source_url', '') or ''
                sentiment = getattr(item, 'sentiment', '') or ''
                author = getattr(item, 'author', '') or ''
                md += f'> "{content}"\n'
                meta = []
                if source_type:
                    meta.append(source_type)
                if sentiment:
                    meta.append(sentiment)
                if author:
                    meta.append(f"@{author}")
                if source_url:
                    meta.append(f"[source]({source_url})")
                if meta:
                    md += f"> — *{' | '.join(meta)}*\n"
                md += "\n"

    # Split top_quotes into brand-related vs segment/trends
    brand_quotes = []
    segment_quotes = []
    SEGMENT_SOURCES = {'tiktok', 'instagram', 'segment_discussion'}
    if ins.top_quotes and isinstance(ins.top_quotes, list):
        for q in ins.top_quotes:
            if isinstance(q, dict):
                src = (q.get('source', q.get('source_type', '')) or '').lower()
                track = q.get('track', None)
                if src in SEGMENT_SOURCES or track == 2:
                    segment_quotes.append(q)
                else:
                    brand_quotes.append(q)
            else:
                brand_quotes.append(q)

    if brand_quotes:
        md += "\n### Additional Brand Quotes from Reviews & Social\n\n"
        md += fmt_top_quotes(brand_quotes)

    md += """---

## 14. Segment & Trend Quotes (TikTok, Instagram, Niche)

These quotes come from segment research and social trends — they reflect the broader market conversation, not direct brand mentions. Useful for understanding audience language, content trends, and cultural context.

"""
    if segment_quotes:
        md += fmt_top_quotes(segment_quotes)
    else:
        md += "(no segment trend quotes)\n"

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

    # ── Section 17b: Ad Creative Patterns (aggregated) ─────────────────────

    acp = getattr(ins, 'ad_creative_patterns', None)
    if acp and isinstance(acp, dict):
        md += """
---

## 17b. Ad Creative Patterns (Aggregated)

*How the brand's ads perform across frameworks, hooks, tones, emotions, and CTAs.*

"""
        total = acp.get("total_analyzed", 0)
        md += f"**Ads Analyzed**: {total}\n"
        avg_hook = acp.get("avg_hook_strength")
        if avg_hook:
            md += f"**Avg Hook Strength**: {avg_hook:.1f}/5\n"
        avg_eff = acp.get("avg_effectiveness")
        if avg_eff:
            md += f"**Avg Effectiveness**: {avg_eff:.1f}/5\n"
        md += "\n"

        for section, label in [
            ("frameworks", "Framework Distribution"),
            ("hook_types", "Hook Type Distribution"),
            ("tones", "Tone Distribution"),
            ("emotions", "Emotion Distribution"),
            ("offer_types", "Offer Types"),
            ("proof_types", "Proof Types"),
            ("cta_placements", "CTA Placements"),
        ]:
            data = acp.get(section, {})
            if data and isinstance(data, dict):
                md += f"**{label}:**\n"
                sorted_items = sorted(data.items(), key=lambda x: x[1] if isinstance(x[1], (int, float)) else 0, reverse=True)
                for k, v in sorted_items[:10]:
                    md += f"- {k}: {v}\n"
                md += "\n"

        top_trans = acp.get("top_transcriptions", [])
        if top_trans and isinstance(top_trans, list):
            md += "### Top Ad Transcriptions\n\n"
            for i, t in enumerate(top_trans, 1):
                if isinstance(t, dict):
                    text = t.get("transcription", t.get("text", str(t)))
                    hook = t.get("hook", "")
                    strength = t.get("hook_strength", "")
                    md += f"**Ad {i}**"
                    if strength:
                        md += f" (hook strength: {strength}/5)"
                    md += f":\n"
                    if hook:
                        md += f"> Hook: \"{hook}\"\n\n"
                    md += f"> \"{text[:500]}\"\n\n"
                elif isinstance(t, str):
                    md += f"**Ad {i}**: \"{t[:500]}\"\n\n"

        ad_examples = acp.get("ad_examples", {})
        if ad_examples and isinstance(ad_examples, dict):
            md += "### Ad Examples by Category\n\n"
            for cat, examples in ad_examples.items():
                md += f"**{cat.replace('_', ' ').title()}:**\n"
                if isinstance(examples, list):
                    for ex in examples[:3]:
                        if isinstance(ex, dict):
                            md += f"- {ex.get('hook', ex.get('text', str(ex)))}\n"
                        else:
                            md += f"- {ex}\n"
                elif isinstance(examples, str):
                    md += f"- {examples}\n"
                md += "\n"

    # ── Section 17c: Per-Ad Creative Analysis ────────────────────────────

    ad_library = getattr(ins, 'ad_library_data', None)
    if ad_library:
        ads_list = []
        if isinstance(ad_library, dict):
            ads_list = ad_library.get("ads", [])
        elif isinstance(ad_library, list):
            ads_list = ad_library

        analyzed_ads = [a for a in ads_list if isinstance(a, dict) and a.get("creative_analysis")]
        if analyzed_ads:
            md += f"""
---

## 17c. Per-Ad Creative Analysis ({len(analyzed_ads)} ads)

*Individual ad breakdowns with transcription, hook, framework, tone, emotion, and effectiveness.*

"""
            for i, ad in enumerate(analyzed_ads, 1):
                ca = ad.get("creative_analysis", {})
                display_fmt = ad.get("display_format", "")
                ad_copy = ad.get("ad_copy", "")
                status = ad.get("status", "")

                md += f"### Ad {i}: {display_fmt}"
                if status:
                    md += f" ({status})"
                md += "\n\n"

                if ad_copy:
                    md += f"**Ad Copy**: \"{ad_copy[:300]}\"\n\n"

                # Key creative analysis fields — deduplicate labels
                _seen_labels = set()
                for field, label in [
                    ("transcription", "Transcription"),
                    ("hook_text", "Hook"),
                    ("hook_type", "Hook Type"),
                    ("hook_strength", "Hook Strength"),
                    ("hook_strength_1to5", "Hook Strength"),
                    ("framework", "Framework"),
                    ("creative_format", "Creative Format"),
                    ("messaging_angle", "Messaging Angle"),
                    ("messaging_angle_text", "Messaging Angle"),
                    ("tone", "Tone"),
                    ("emotion", "Emotion"),
                    ("target_persona", "Target Persona"),
                    ("target_audience_inferred", "Target Audience"),
                    ("pain_point_addressed", "Pain Point Addressed"),
                    ("pain_points_text", "Pain Points"),
                    ("value_prop_highlighted", "Value Prop"),
                    ("value_props_text", "Value Props"),
                    ("cta_text", "CTA"),
                    ("cta_all", "CTA"),
                    ("cta_placement", "CTA Placement"),
                    ("offer_type", "Offer"),
                    ("urgency_element", "Urgency"),
                    ("proof_type", "Proof Type"),
                    ("visual_type", "Visual Type"),
                    ("talent_type", "Talent"),
                    ("funnel_stage", "Funnel Stage"),
                    ("effectiveness_score", "Effectiveness"),
                    ("effectiveness_score_1to5", "Effectiveness"),
                    ("effectiveness", "Effectiveness"),
                    ("angle_label", "Angle Label"),
                    ("psychological_triggers", "Psychological Triggers"),
                    ("emotional_triggers", "Emotional Triggers"),
                    ("alternative_hooks", "Alternative Hooks"),
                ]:
                    val = ca.get(field)
                    if not val or label in _seen_labels:
                        continue
                    _seen_labels.add(label)
                    if isinstance(val, list):
                        md += f"- **{label}**: {', '.join(str(v) for v in val)}\n"
                    elif field == "transcription" and len(str(val)) > 20:
                        md += f"- **{label}**: \"{str(val)[:600]}\"\n"
                    elif "strength" in field or "effectiveness" in field or "1to5" in field:
                        md += f"- **{label}**: {val}/5\n"
                    else:
                        md += f"- **{label}**: {val}\n"

                # High-fidelity visual description (IMAGE + VIDEO)
                hfd = ca.get("high_fidelity_description", "")
                if hfd:
                    md += f"- **Visual Description**: {hfd}\n"

                # Strategic summary
                strat = ca.get("strategic_summary", "")
                if strat:
                    md += f"- **Strategic Summary**: {strat}\n"

                # Ad summary
                ad_sum = ca.get("ad_summary", "")
                if ad_sum:
                    md += f"- **Ad Summary**: {ad_sum}\n"

                # Scene breakdown (for video)
                scenes = ca.get("scene_breakdown", [])
                if scenes and isinstance(scenes, list) and len(scenes) > 1:
                    md += "- **Scene Breakdown**:\n"
                    for scene in scenes:
                        if isinstance(scene, dict):
                            ts = scene.get("timestamp_start", "")
                            te = scene.get("timestamp_end", "")
                            stype = scene.get("scene_type", "")
                            vdesc = scene.get("visual_description", "")
                            ts_str = f"[{ts}-{te}] " if ts else ""
                            type_str = f"**{stype}**: " if stype else ""
                            md += f"  - {ts_str}{type_str}{vdesc[:200]}\n"

                md += "\n"

    # ── Section 17d: Competitor Ads Analysis ─────────────────────────────

    comp_ads = getattr(ins, 'competitor_ads_data', None)
    if comp_ads and isinstance(comp_ads, list):
        md += """
---

## 17d. Competitor Ads Analysis

*Creative analysis of competitor advertising — frameworks, hooks, angles they use.*

"""
        for comp_entry in comp_ads:
            if not isinstance(comp_entry, dict):
                continue
            comp_name = comp_entry.get("competitor_name", "Unknown")
            comp_ad_list = comp_entry.get("ads", [])
            analyzed_comp = [a for a in comp_ad_list if isinstance(a, dict) and a.get("creative_analysis")]

            md += f"### {comp_name} ({len(analyzed_comp)} ads analyzed)\n\n"

            for j, ad in enumerate(analyzed_comp[:10], 1):
                ca = ad.get("creative_analysis", {})
                ad_copy = ad.get("ad_copy", "")
                display_fmt = ad.get("display_format", "")

                md += f"**Ad {j}** ({display_fmt})"
                hook = ca.get("hook_text", "")
                if hook:
                    md += f": \"{hook}\""
                md += "\n"

                compact_fields = []
                for field in ["framework", "messaging_angle", "tone", "emotion", "hook_strength", "funnel_stage", "effectiveness"]:
                    val = ca.get(field)
                    if val:
                        compact_fields.append(f"{field}={val}")
                if compact_fields:
                    md += f"  [{' | '.join(compact_fields)}]\n"
                if ad_copy:
                    md += f"  Copy: \"{ad_copy[:200]}\"\n"
                transcription = ca.get("transcription", "")
                if transcription and len(transcription) > 20:
                    md += f"  Transcription: \"{transcription[:400]}\"\n"
                hfd = ca.get("high_fidelity_description", "")
                if hfd:
                    md += f"  Visual: {hfd[:300]}\n"
                strat = ca.get("strategic_summary", "")
                if strat:
                    md += f"  Strategy: {strat[:300]}\n"
                md += "\n"

    # ── Section 17e: Content Insights ────────────────────────────────────

    content_ins = getattr(ins, 'content_insights', None)
    if content_ins and isinstance(content_ins, list):
        md += """
---

## 17e. Content Insights

"""
        for ci in content_ins:
            if isinstance(ci, dict):
                md += f"- **{ci.get('insight', ci.get('title', str(ci)))}**\n"
                for k, v in ci.items():
                    if k not in ('insight', 'title') and v:
                        md += f"  - {k.replace('_', ' ').title()}: {v}\n"
            else:
                md += f"- {ci}\n"
        md += "\n"

    # ── Section 17f: Data by Topic ───────────────────────────────────────

    data_by_topic = getattr(ins, 'data_by_topic', None)
    if data_by_topic and isinstance(data_by_topic, dict):
        md += """
---

## 17f. Customer Data by Topic

*Customer feedback organized by topic — raw quotes with sentiment and source.*

"""
        for topic, items in data_by_topic.items():
            if not isinstance(items, list) or not items:
                continue
            md += f"### {topic.replace('_', ' ').title()} ({len(items)} items)\n\n"
            for item in items[:15]:
                if isinstance(item, dict):
                    content = item.get("content", item.get("text", ""))[:300]
                    source = item.get("source_type", "")
                    sentiment = item.get("sentiment", "")
                    score = item.get("sentiment_score")
                    score_str = f" ({score:+.2f})" if score is not None else ""
                    md += f'> "{content}"\n'
                    meta = []
                    if source:
                        meta.append(source)
                    if sentiment:
                        meta.append(f"{sentiment}{score_str}")
                    if meta:
                        md += f"> — *{' | '.join(meta)}*\n"
                    md += "\n"
                elif isinstance(item, str):
                    md += f'> "{item[:300]}"\n\n'

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

    # ── Section 19: Proto-ICP Clusters (complete) ──────────────────────────

    proto_icps = ins.proto_icps
    if proto_icps and isinstance(proto_icps, list) and len(proto_icps) > 0:
        md += """
---

## 19. Proto-ICP Clusters (Voice of Customer)

These clusters are built from real customer language, grouped by **trigger** (why they started searching) and **blocker** (what holds them back). Each cluster includes representative verbatim snippets with sources.

"""
        for i, cluster in enumerate(proto_icps, 1):
            if not isinstance(cluster, dict):
                continue
            trigger = cluster.get('trigger', cluster.get('primary_trigger', 'Unknown'))
            blocker = cluster.get('blocker', cluster.get('blocker_type', 'Unknown'))
            count = cluster.get('snippet_count', cluster.get('count', 0))
            md += f"### Cluster {i}: {trigger} × {blocker} ({count} snippets)\n\n"

            # Outcome distribution
            outcomes = cluster.get('outcome_distribution', cluster.get('desired_outcomes', {}))
            if outcomes and isinstance(outcomes, dict):
                md += "**Desired Outcomes**: "
                md += ", ".join(f"{k}: {v}" for k, v in outcomes.items() if v)
                md += "\n\n"

            # Proof types
            proofs = cluster.get('proof_type_distribution', cluster.get('proof_types', {}))
            if proofs and isinstance(proofs, dict):
                md += "**Proof Types Trusted**: "
                md += ", ".join(f"{k}: {v}" for k, v in proofs.items() if v)
                md += "\n\n"

            # Language cues
            cues = cluster.get('top_language_cues', cluster.get('language_cues', []))
            if cues:
                cue_list = cues[:10] if isinstance(cues, list) else [cues]
                md += f"**Language Cues**: {', '.join(str(c) for c in cue_list)}\n\n"

            # Representative snippets
            snippets = cluster.get('representative_snippets', cluster.get('snippets', []))
            if snippets and isinstance(snippets, list):
                for s in snippets[:5]:
                    if isinstance(s, dict):
                        content = s.get('content', s.get('text', ''))[:300]
                        source = s.get('source_url', s.get('url', ''))
                        source_type = s.get('source_type', '')
                        md += f'> "{content}"\n'
                        if source_type or source:
                            md += f"> — *{source_type}*"
                            if source:
                                md += f" [{source}]({source})"
                            md += "\n"
                        md += "\n"
                    elif isinstance(s, str):
                        md += f'> "{s[:300]}"\n\n'
            md += "\n"

    # ── Section 19b: Creative Target Personas (CTPs) ────────────────────

    ctp_data = getattr(ins, 'ctp_data', None) or []
    if ctp_data and isinstance(ctp_data, list):
        ctp_stats = getattr(ins, 'ctp_stats', None) or {}
        total_snippets = ctp_stats.get("total_snippets", sum(c.get("snippet_count", 0) for c in ctp_data))
        md += f"""
---

## 19b. Creative Target Personas (CTPs)

*{len(ctp_data)} personas discovered from {total_snippets} customer snippets.*

"""
        for ctp in ctp_data:
            ctp_id = ctp.get("ctp_id", "")
            name = ctp.get("ctp_name", "Unknown")
            weight = ctp.get("weight", 0)
            stance = ctp.get("general_stance", "")
            count = ctp.get("snippet_count", 0)
            cd6 = ctp.get("core_insight_general", "")
            product_belief = ctp.get("core_insight_product_anchored", "")
            source_path = ctp.get("source", "")

            md += f"### {ctp_id}: {name} (Weight: {weight}/10, {count} snippets)\n\n"
            md += f"**Stance**: {stance}"
            stance_tags = ctp.get("stance_tags", [])
            if stance_tags and isinstance(stance_tags, list):
                md += f" | **Tags**: {', '.join(stance_tags)}"
            if source_path:
                md += f" | **Path**: {source_path}"
            md += "\n\n"

            if cd6:
                md += f"**Core Insight:** \"{cd6}\"\n\n"
            if product_belief:
                md += f"**Product-Anchored Belief:** \"{product_belief}\"\n\n"

            psychology = ctp.get("archetype_psychology") or ctp.get("psychology", "")
            if psychology:
                md += f"**Psychology:** {psychology}\n\n"

            unique = ctp.get("what_makes_them_unique", "")
            if unique:
                md += f"**What Makes Them Unique:** {unique}\n\n"

            counter = ctp.get("counter_segment", "")
            if counter:
                md += f"**Counter-Segment:** {counter}\n\n"

            markers = ctp.get("behavioral_markers", [])
            if markers and isinstance(markers, list):
                md += "**Behavioral Markers:** " + " · ".join(markers) + "\n\n"

            decision_factors = ctp.get("decision_factors", [])
            if decision_factors and isinstance(decision_factors, list):
                md += "**Decision Factors:**\n"
                for df in decision_factors:
                    if isinstance(df, dict):
                        factor = df.get("factor", str(df))
                        priority = df.get("priority", "")
                        prio_tag = f" [{priority}]" if priority else ""
                        md += f"- {factor}{prio_tag}\n"
                    else:
                        md += f"- {df}\n"
                md += "\n"

            vocabulary = ctp.get("vocabulary", [])
            if vocabulary and isinstance(vocabulary, list):
                md += "**Vocabulary:** " + ", ".join(f'"{v}"' for v in vocabulary) + "\n\n"

            # Pain points
            pain_points = ctp.get("pain_points", [])
            if pain_points:
                md += "**Pain Points:**\n"
                for pp in pain_points:
                    if isinstance(pp, dict):
                        md += f"- {pp.get('pain_point', str(pp))}\n"
                    else:
                        md += f"- {pp}\n"
                md += "\n"

            # Desires (was missing)
            desires = ctp.get("desires", [])
            if desires and isinstance(desires, list):
                md += "**Desires:**\n"
                for d in desires:
                    if isinstance(d, dict):
                        md += f"- {d.get('desire', str(d))}\n"
                    else:
                        md += f"- {d}\n"
                md += "\n"

            # Barriers & objections (was missing)
            barriers = ctp.get("barriers_objections", [])
            if barriers and isinstance(barriers, list):
                md += "**Barriers / Objections:**\n"
                for bo in barriers:
                    if isinstance(bo, dict):
                        btype = bo.get("type", "")
                        prompt = bo.get("prompt", str(bo))
                        tag = f" [{btype}]" if btype else ""
                        md += f"- {prompt}{tag}\n"
                    else:
                        md += f"- {bo}\n"
                md += "\n"

            # Kill signals (was missing)
            kill_signals = ctp.get("kill_signals", {})
            if kill_signals:
                if isinstance(kill_signals, dict):
                    existence = kill_signals.get("existence", [])
                    if existence and isinstance(existence, list):
                        md += "**Kill Signals:**\n"
                        for ks in existence:
                            md += f"- {ks}\n"
                        md += "\n"
                elif isinstance(kill_signals, list):
                    md += "**Kill Signals:**\n"
                    for ks in kill_signals:
                        md += f"- {ks}\n"
                    md += "\n"

            # Hooks & value props per CTP
            rec_hooks = ctp.get("recommended_hooks", [])
            if rec_hooks and isinstance(rec_hooks, list):
                md += "**Recommended Hooks:**\n"
                for h in rec_hooks:
                    if isinstance(h, dict):
                        text = h.get("hook", h.get("text", str(h)))
                        src_tag = h.get("source", "")
                        tag_str = f" `{src_tag}`" if src_tag else ""
                        md += f"- {text}{tag_str}\n"
                    else:
                        md += f"- {h}\n"
                md += "\n"

            rec_vp = ctp.get("recommended_value_props", [])
            if rec_vp and isinstance(rec_vp, list):
                md += "**Recommended Value Props:**\n"
                for vp in rec_vp:
                    if isinstance(vp, dict):
                        text = vp.get("value_prop", vp.get("text", str(vp)))
                        md += f"- {text}\n"
                    else:
                        md += f"- {vp}\n"
                md += "\n"

            frameworks = ctp.get("frameworks_that_resonate", [])
            if frameworks and isinstance(frameworks, list):
                md += "**Frameworks That Resonate:**\n"
                for fw in frameworks:
                    if isinstance(fw, dict):
                        name_fw = fw.get("framework", fw.get("name", str(fw)))
                        rationale = fw.get("rationale", "")
                        md += f"- **{name_fw}**"
                        if rationale:
                            md += f" — {rationale}"
                        md += "\n"
                    else:
                        md += f"- {fw}\n"
                md += "\n"

            # Tone & Emotion Arc — handle both string and dict
            tone_arc = ctp.get("tone_and_emotion_arc", "")
            if tone_arc:
                if isinstance(tone_arc, dict):
                    primary_tone = tone_arc.get("primary_tone", "")
                    emotion_arc = tone_arc.get("emotion_arc", "")
                    rationale = tone_arc.get("rationale", "")
                    md += f"**Tone & Emotion Arc:**\n"
                    if primary_tone:
                        md += f"- Tone: {primary_tone}\n"
                    if emotion_arc:
                        md += f"- Arc: {emotion_arc}\n"
                    if rationale:
                        md += f"- Rationale: {rationale}\n"
                    md += "\n"
                else:
                    md += f"**Tone & Emotion Arc:** {tone_arc}\n\n"

            ad_gap = ctp.get("ad_creative_gap", "")
            if ad_gap:
                md += f"**Ad Creative Gap:** {ad_gap}\n\n"

            anti_patterns = ctp.get("anti_patterns", [])
            if anti_patterns and isinstance(anti_patterns, list):
                md += "**Anti-Patterns:** " + " · ".join(anti_patterns) + "\n\n"

            # Source distribution (was missing)
            source_dist = ctp.get("source_distribution", {})
            if source_dist and isinstance(source_dist, dict):
                sorted_sources = sorted(source_dist.items(), key=lambda x: x[1], reverse=True)
                md += "**Source Distribution:** " + " · ".join(f"{s}: {c}" for s, c in sorted_sources) + "\n\n"

            # Evidence quotes
            evidence_quotes = ctp.get("evidence_quotes", [])
            if evidence_quotes and isinstance(evidence_quotes, list):
                md += "**Evidence Quotes:**\n"
                for eq in evidence_quotes[:5]:
                    if isinstance(eq, dict):
                        md += f'> "{eq.get("quote", str(eq))}"\n\n'
                    else:
                        md += f'> "{eq}"\n\n'

            # Representative snippets (was missing — raw cluster verbatims)
            rep_snippets = ctp.get("representative_snippets", [])
            if rep_snippets and isinstance(rep_snippets, list):
                md += f"**Representative Verbatims ({len(rep_snippets)} samples):**\n"
                for rs in rep_snippets:
                    if isinstance(rs, dict):
                        content = rs.get("content", "")[:300]
                        source = rs.get("source_type", "")
                        sent = rs.get("sentiment", "")
                        md += f'> "{content}"\n'
                        meta = []
                        if source:
                            meta.append(source)
                        if sent:
                            meta.append(sent)
                        if meta:
                            md += f"> — *{' | '.join(meta)}*\n"
                        md += "\n"
                    elif isinstance(rs, str):
                        md += f'> "{rs[:300]}"\n\n'

            md += "\n"

    # ── Section 19c: CTP Hypothesis Layer ─────────────────────────────────

    ctp_hypothesis = getattr(ins, 'ctp_hypothesis', None) or []
    if ctp_hypothesis and isinstance(ctp_hypothesis, list):
        md += """
---

## 19c. CTP Hypothesis Layer (Strategy per Persona)

*Demographics, angles, frameworks, tone, and emotion per CTP.*

"""
        hyp_by_id = {h.get("ctp_id", ""): h for h in ctp_hypothesis if isinstance(h, dict)}
        for ctp in ctp_data:
            ctp_id = ctp.get("ctp_id", "")
            ctp_name = ctp.get("ctp_name", "Unknown")
            hyp = hyp_by_id.get(ctp_id, {})
            if not hyp:
                continue

            md += f"### {ctp_id}: {ctp_name}\n\n"

            # Demographics — full
            demo = hyp.get("demographic_variables", {})
            if demo and isinstance(demo, dict):
                md += "**Demographic Variables:**\n"
                for field, label in [("age_range", "Age"), ("gender_skew", "Gender"),
                                     ("income_level", "Income"), ("education", "Education"),
                                     ("platform_affinity", "Platforms"), ("geo_notes", "Geo"),
                                     ("aspirations", "Aspirations"), ("lifestyle_markers", "Lifestyle")]:
                    val = demo.get(field)
                    if val:
                        if isinstance(val, list):
                            val = ", ".join(str(v) for v in val)
                        md += f"- {label}: {val}\n"
                md += "\n"

            # Angles — full with description, awareness, emotional trigger, evidence
            angles = hyp.get("angles", [])
            if angles:
                md += "**Angles (CD7):**\n"
                for i, angle in enumerate(angles, 1):
                    if isinstance(angle, dict):
                        name_a = angle.get("angle_name", f"Angle {i}")
                        vtag = angle.get("validation_tag", "hypothesis")
                        desc = angle.get("angle_description", "")
                        awareness = angle.get("awareness_level", "")
                        trigger = angle.get("emotional_trigger", "")
                        evidence = angle.get("validation_evidence", "")
                        md += f"- **{name_a}** [{vtag}]"
                        if awareness:
                            md += f" — {awareness}"
                        md += "\n"
                        if desc:
                            md += f"  {desc}\n"
                        if trigger:
                            md += f"  *Emotional trigger:* {trigger}\n"
                        if evidence:
                            md += f"  *Evidence:* {evidence}\n"
                    else:
                        md += f"- {angle}\n"
                md += "\n"

            # Funnel stage + rationale
            funnel_s = hyp.get("funnel_stage", {})
            if funnel_s and isinstance(funnel_s, dict):
                md += f"**Funnel Stage (CD8):** {funnel_s.get('stage', '?')}\n"
                rationale = funnel_s.get("rationale", "")
                if rationale:
                    md += f"  *Rationale:* {rationale}\n"
                md += "\n"

            # Framework + rationale
            fw = hyp.get("framework_tactic", {})
            if fw and isinstance(fw, dict):
                parts = [fw.get("primary", ""), fw.get("secondary", "")]
                md += f"**Framework / Tactic (CD10):** {' + '.join(p for p in parts if p)}\n"
                rationale = fw.get("rationale", "")
                if rationale:
                    md += f"  *Rationale:* {rationale}\n"
                md += "\n"

            # Visual style (was missing entirely)
            vs = hyp.get("visual_style", {})
            if vs and isinstance(vs, dict):
                style = vs.get("style", "")
                rationale = vs.get("rationale", "")
                if style:
                    md += f"**Visual Style (CD11):** {style}\n"
                    if rationale:
                        md += f"  *Rationale:* {rationale}\n"
                    md += "\n"

            # Narrative driver (was missing entirely)
            nd = hyp.get("narrative_driver", {})
            if nd and isinstance(nd, dict):
                driver = nd.get("driver", "")
                rationale = nd.get("rationale", "")
                if driver:
                    md += f"**Narrative Driver (CD12):** {driver}\n"
                    if rationale:
                        md += f"  *Rationale:* {rationale}\n"
                    md += "\n"

            # Tone + rationale
            tone = hyp.get("tone", {})
            if tone and isinstance(tone, dict):
                parts = [tone.get("primary", ""), tone.get("secondary", "")]
                md += f"**Tone (CD13):** {' + '.join(p for p in parts if p)}\n"
                rationale = tone.get("rationale", "")
                if rationale:
                    md += f"  *Rationale:* {rationale}\n"
                md += "\n"

            # Emotion + arc + rationale
            emotion = hyp.get("emotion", {})
            if emotion and isinstance(emotion, dict):
                primary_em = emotion.get("primary_emotion", "")
                arc = emotion.get("arc", "")
                rationale = emotion.get("rationale", "")
                if primary_em or arc:
                    md += f"**Emotion (CD14):** {primary_em}"
                    if arc:
                        md += f" — Arc: {arc}"
                    md += "\n"
                    if rationale:
                        md += f"  *Rationale:* {rationale}\n"
                    md += "\n"

            md += "\n"

    # ── Section 19d: Target Personas (TOFU Prospects) ─────────────────────

    target_personas = getattr(ins, 'target_personas', None) or []
    if target_personas and isinstance(target_personas, list):
        from .ctp_export import _render_target_personas
        md += "\n---\n\n## 19d. " + _render_target_personas(target_personas).lstrip("# ")

    # ── Section 19e: Community Dialect ────────────────────────────────────

    community_dialect = getattr(ins, 'community_dialect', None) or []
    if community_dialect:
        md += """
---

## 19e. Community Dialect

*Terms and phrases used by this brand's community — use these in copy for authenticity.*

"""
        terms = []
        for term in community_dialect:
            if isinstance(term, dict):
                terms.append(term.get('term', str(term)))
            else:
                terms.append(str(term))
        md += ", ".join(f'"{t}"' for t in terms) + "\n\n"

    # ── Section 19f: Proto-ICP Recommendations ───────────────────────────

    proto_recs = getattr(ins, 'proto_icp_recommendations', None) or []
    if proto_recs and isinstance(proto_recs, list):
        md += """
---

## 19f. Proto-ICP Recommendations

"""
        for i, rec in enumerate(proto_recs, 1):
            if isinstance(rec, dict):
                md += f"{i}. **{rec.get('recommendation', rec.get('name', str(rec)))}**\n"
                for k, v in rec.items():
                    if k not in ('recommendation', 'name') and v:
                        md += f"   - {k.replace('_', ' ').title()}: {v}\n"
            else:
                md += f"{i}. {rec}\n"
        md += "\n"

    # ── Section 20: Raw Customer Verbatims by Source ─────────────────────

    if raw_data:
        md += """
---

## 20. Raw Customer Verbatims by Source

Real customer feedback with source attribution, sentiment, and intake classification. This is the raw evidence base for persona building and creative strategy.

"""
        # Group by source_type
        from collections import defaultdict
        by_source = defaultdict(list)
        for item in raw_data:
            st = getattr(item, 'source_type', None) or 'unknown'
            by_source[st].append(item)

        for source_type in sorted(by_source.keys()):
            items = by_source[source_type]
            md += f"### {source_type.replace('_', ' ').title()} ({len(items)} items)\n\n"

            # Take top 50 per source, sorted by relevance
            shown = items[:50]
            for item in shown:
                content = getattr(item, 'content', '') or ''
                if not content.strip():
                    continue
                content = content[:500].replace('\n', ' ').strip()
                source_url = getattr(item, 'source_url', '') or ''
                author = getattr(item, 'author', '') or ''
                sentiment = getattr(item, 'sentiment', '') or ''
                sentiment_score = getattr(item, 'sentiment_score', None)
                posted_at = getattr(item, 'posted_at', None)

                md += f'> "{content}"\n'
                meta_parts = []
                if author:
                    meta_parts.append(f"@{author}")
                if sentiment:
                    score_str = f" ({sentiment_score:.2f})" if sentiment_score is not None else ""
                    meta_parts.append(f"{sentiment}{score_str}")
                if posted_at:
                    meta_parts.append(str(posted_at)[:10])
                if source_url:
                    meta_parts.append(f"[source]({source_url})")
                if meta_parts:
                    md += f"> — *{' | '.join(meta_parts)}*\n"

                # Intake engine classifications
                trigger = getattr(item, 'primary_trigger', None)
                blocker = getattr(item, 'blocker_type', None)
                outcome = getattr(item, 'desired_outcome_level', None)
                proof = getattr(item, 'proof_type_trusted', None)
                lang_cues = getattr(item, 'language_cues', None)
                intake_parts = []
                if trigger:
                    intake_parts.append(f"trigger={trigger}")
                if blocker:
                    intake_parts.append(f"blocker={blocker}")
                if outcome:
                    intake_parts.append(f"outcome={outcome}")
                if proof:
                    intake_parts.append(f"proof={proof}")
                if lang_cues and isinstance(lang_cues, list):
                    intake_parts.append(f"cues={', '.join(lang_cues[:5])}")
                if intake_parts:
                    md += f"> *[{' | '.join(intake_parts)}]*\n"

                md += "\n"

            if len(items) > 50:
                md += f"*... and {len(items) - 50} more {source_type} items*\n\n"

    # ── Section 21: Sentiment Distribution by Source ─────────────────────

    if raw_data:
        md += """
---

## 21. Sentiment Distribution by Source

| Source | Total | Positive | Neutral | Negative | Avg Score |
|--------|-------|----------|---------|----------|-----------|
"""
        from collections import defaultdict
        sent_stats = defaultdict(lambda: {'total': 0, 'positive': 0, 'neutral': 0, 'negative': 0, 'score_sum': 0.0, 'score_count': 0})
        for item in raw_data:
            st = getattr(item, 'source_type', None) or 'unknown'
            sentiment = (getattr(item, 'sentiment', '') or '').lower()
            score = getattr(item, 'sentiment_score', None)
            sent_stats[st]['total'] += 1
            if 'positive' in sentiment:
                sent_stats[st]['positive'] += 1
            elif 'negative' in sentiment:
                sent_stats[st]['negative'] += 1
            else:
                sent_stats[st]['neutral'] += 1
            if score is not None:
                sent_stats[st]['score_sum'] += float(score)
                sent_stats[st]['score_count'] += 1

        for source in sorted(sent_stats.keys()):
            s = sent_stats[source]
            avg = f"{s['score_sum'] / s['score_count']:.3f}" if s['score_count'] > 0 else "N/A"
            md += f"| {source.replace('_', ' ').title()} | {s['total']} | {s['positive']} | {s['neutral']} | {s['negative']} | {avg} |\n"

        md += "\n"

    # =======================================================
    # New Fase 3 sections: Angle Bank advanced, Failed/Transformation/Weak,
    # UGC Briefs, Funnel Strategy, Post-Purchase Survey.
    # Each is gated by "if data present" so sessions without the new fields
    # still export cleanly with no empty headers.
    # =======================================================

    def safe_get(ins_obj, attr, default):
        """Read an attribute from the Insight ORM; tolerant of None/missing."""
        if ins_obj is None:
            return default
        val = getattr(ins_obj, attr, None)
        return val if val is not None else default

    # Advanced Angle Bank (messaging_angles enriched with awareness_level / priority / trigger)
    angles = safe_get(insight, 'messaging_angles', [])
    advanced_angles = [a for a in angles if isinstance(a, dict) and (a.get('awareness_level') or a.get('emotional_trigger') or a.get('creative_priority'))]
    if advanced_angles:
        md += "\n## 22. Angle Bank (Enriched)\n\n"
        md += "*Each angle is tagged with awareness level, emotional trigger, creative priority, and format fit.*\n\n"
        for i, angle in enumerate(advanced_angles, 1):
            name = angle.get('name', f'Angle {i}')
            hook = angle.get('hook', '')
            priority = angle.get('creative_priority', '')
            level = angle.get('awareness_level', '')
            trigger = angle.get('emotional_trigger', '')
            formats = angle.get('best_fit_formats') or []
            source_q = angle.get('source_quote', '')
            desc = angle.get('description', '')
            md += f"### {i}. {name}"
            tags = [t for t in [priority, level, trigger] if t]
            if tags:
                md += " _(" + " · ".join(tags) + ")_"
            md += "\n\n"
            if hook:
                md += f"> **Hook:** \"{hook}\"\n\n"
            if desc:
                md += f"{desc}\n\n"
            if formats:
                md += f"**Best formats:** {', '.join(formats)}\n\n"
            if source_q:
                md += f"**Source quote:** _\"{source_q}\"_\n\n"

    # Failed Solution Angles
    failed_solutions = safe_get(insight, 'failed_solution_angles', [])
    if failed_solutions:
        md += "\n## 23. Failed Solution Angles\n\n"
        md += "*What customers tried before — the strongest hooks for solution-aware audiences.*\n\n"
        for i, angle in enumerate(failed_solutions, 1):
            if not isinstance(angle, dict):
                continue
            md += f"### {i}. {angle.get('solution_tried', 'Unknown solution')}\n\n"
            if angle.get('why_it_failed'):
                md += f"**Why it failed:** {angle['why_it_failed']}\n\n"
            if angle.get('verbatim'):
                md += f"> \"{angle['verbatim']}\"\n\n"
            if angle.get('hook'):
                md += f"**Hook:** \"{angle['hook']}\"\n\n"

    # Transformation Angles
    transforms = safe_get(insight, 'transformation_angles', [])
    if transforms:
        md += "\n## 24. Transformation Angles\n\n"
        md += "*Before → After shifts described by real customers.*\n\n"
        for i, angle in enumerate(transforms, 1):
            if not isinstance(angle, dict):
                continue
            before = angle.get('before_state', '')
            after = angle.get('after_state', '')
            md += f"### {i}. {before} → {after}\n\n"
            if angle.get('verbatim'):
                md += f"> \"{angle['verbatim']}\"\n\n"
            if angle.get('hook'):
                md += f"**Hook:** \"{angle['hook']}\"\n\n"

    # Weak Signals
    weak_signals = safe_get(insight, 'weak_signals', [])
    if weak_signals:
        md += "\n## 25. Weak Signals (Low frequency, high creative potential)\n\n"
        md += "*Rare quotes with unusual hook potential — angles nobody is running.*\n\n"
        for i, signal in enumerate(weak_signals, 1):
            if not isinstance(signal, dict):
                continue
            md += f"### Signal {i}\n\n"
            if signal.get('quote'):
                md += f"> \"{signal['quote']}\"\n\n"
            if signal.get('creative_potential'):
                md += f"**Why it matters:** {signal['creative_potential']}\n\n"
            variations = signal.get('hook_variations') or []
            if variations:
                md += "**Hook variations:**\n"
                for v in variations:
                    md += f"- \"{v}\"\n"
                md += "\n"

    # UGC Creator Briefs
    ugc_briefs = safe_get(insight, 'ugc_briefs', [])
    if ugc_briefs:
        md += "\n## 26. UGC Creator Briefs\n\n"
        md += "*Ready-to-send briefs for external UGC creators. Non-negotiable hooks + talking points + production notes.*\n\n"
        for i, brief in enumerate(ugc_briefs, 1):
            if not isinstance(brief, dict):
                continue
            md += f"### {i}. {brief.get('brief_name', f'Brief {i}')}"
            tags = [t for t in [brief.get('angle_type'), brief.get('awareness_level')] if t]
            if tags:
                md += " _(" + " · ".join(tags) + ")_"
            md += "\n\n"
            if brief.get('target_persona'):
                md += f"**Target persona:** {brief['target_persona']}\n\n"
            if brief.get('overview'):
                md += f"{brief['overview']}\n\n"
            hook_nn = brief.get('hook_non_negotiable') or {}
            if hook_nn.get('exact_line'):
                md += f"**Hook (non-negotiable):** \"{hook_nn['exact_line']}\"\n\n"
                if hook_nn.get('visual_direction'):
                    md += f"- Visual: {hook_nn['visual_direction']}\n"
                if hook_nn.get('energy'):
                    md += f"- Energy: {hook_nn['energy']}\n"
                if hook_nn.get('what_not_to_do'):
                    md += f"- Do NOT: {hook_nn['what_not_to_do']}\n"
                md += "\n"
            talking_points = brief.get('body_talking_points') or []
            if talking_points:
                md += "**Talking points:**\n"
                for j, tp in enumerate(talking_points, 1):
                    md += f"{j}. {tp}\n"
                md += "\n"
            if brief.get('emotional_journey'):
                md += f"**Emotional arc:** {brief['emotional_journey']}\n\n"
            close = brief.get('close') or {}
            if close.get('how_it_ends') or close.get('cta_language'):
                md += f"**Close:** {close.get('how_it_ends','')}"
                if close.get('cta_language'):
                    md += f" → \"{close['cta_language']}\""
                md += "\n\n"

    # Full Funnel Creative Strategy
    funnel = safe_get(insight, 'funnel_strategy', None)
    if isinstance(funnel, dict) and funnel and not funnel.get('_fallback'):
        md += "\n## 27. Full Funnel Creative Strategy\n\n"
        diagnosis = funnel.get('account_diagnosis') or {}
        if diagnosis:
            md += "### Account Diagnosis\n\n"
            for k, v in diagnosis.items():
                if isinstance(v, str) and v:
                    md += f"- **{k.replace('_',' ').title()}:** {v}\n"
                elif isinstance(v, list) and v:
                    md += f"- **{k.replace('_',' ').title()}:** {', '.join(str(x) for x in v)}\n"
            md += "\n"

        personas = funnel.get('persona_architecture') or []
        if personas:
            md += "### Persona Architecture\n\n"
            for p in personas:
                if not isinstance(p, dict):
                    continue
                md += f"- **{p.get('persona_name','Persona')}** _({p.get('awareness_level','?')})_: {p.get('description','')}\n"
                if p.get('hook_direction'):
                    md += f"  - Hook direction: \"{p['hook_direction']}\"\n"
            md += "\n"

        funnel_map = funnel.get('funnel_map') or {}
        if funnel_map:
            md += "### Funnel Map\n\n"
            for stage_key in ('top_of_funnel', 'middle_of_funnel', 'bottom_of_funnel'):
                stage = funnel_map.get(stage_key)
                if not isinstance(stage, dict):
                    continue
                md += f"**{stage_key.replace('_',' ').title()}**\n"
                if stage.get('goal'):
                    md += f"- Goal: {stage['goal']}\n"
                if stage.get('recommended_formats'):
                    md += f"- Formats: {', '.join(str(f) for f in stage['recommended_formats'])}\n"
                if stage.get('example_hook'):
                    md += f"- Example hook: \"{stage['example_hook']}\"\n"
                if stage.get('budget_allocation'):
                    md += f"- Budget: {stage['budget_allocation']}\n"
                md += "\n"

        roadmap = funnel.get('ninety_day_roadmap') or {}
        if roadmap:
            md += "### 90-Day Creative Roadmap\n\n"
            for phase_key in ('phase_1_foundation', 'phase_2_validation', 'phase_3_compounding'):
                phase = roadmap.get(phase_key)
                if not isinstance(phase, dict):
                    continue
                md += f"**{phase_key.replace('_',' ').title()}** — {phase.get('weeks','')}\n"
                for k, v in phase.items():
                    if k == 'weeks':
                        continue
                    if isinstance(v, list) and v:
                        md += f"- {k.replace('_',' ').title()}: {', '.join(str(x) for x in v)}\n"
                    elif isinstance(v, str) and v:
                        md += f"- {k.replace('_',' ').title()}: {v}\n"
                md += "\n"

        briefs = funnel.get('first_three_briefs') or []
        if briefs:
            md += "### First Three Priority Briefs\n\n"
            for b in briefs:
                if not isinstance(b, dict):
                    continue
                md += f"{b.get('priority','?')}. **{b.get('angle','')}** ({b.get('target_persona','')}, {b.get('awareness_level','')})\n"
                if b.get('format'):
                    md += f"   - Format: {b['format']}\n"
                if b.get('hook_direction'):
                    md += f"   - Hook: \"{b['hook_direction']}\"\n"
                if b.get('why_first'):
                    md += f"   - Why first: {b['why_first']}\n"
            md += "\n"

    # Post-Purchase Survey
    survey = safe_get(insight, 'post_purchase_survey', None)
    if isinstance(survey, dict) and survey and not survey.get('_fallback'):
        md += "\n## 28. Post-Purchase Survey Questions\n\n"
        md += "*Survey designed to produce copy, not satisfaction ratings.*\n\n"
        best = survey.get('single_best_question') or {}
        if best.get('question'):
            md += f"### The Single Best Question\n\n> \"{best['question']}\"\n\n"
            if best.get('why_its_the_best'):
                md += f"{best['why_its_the_best']}\n\n"
        core_five = survey.get('core_five') or []
        if core_five:
            md += "### Core Questions\n\n"
            for i, q in enumerate(core_five, 1):
                if not isinstance(q, dict):
                    continue
                md += f"{i}. **\"{q.get('question','')}\"**\n"
                if q.get('creative_output_designed_for'):
                    md += f"   - Designed to produce: {q['creative_output_designed_for']}\n"
                if q.get('awareness_level_surfaced'):
                    md += f"   - Surfaces: {q['awareness_level_surfaced']}\n"
                if q.get('example_winning_response'):
                    md += f"   - Example response: _\"{q['example_winning_response']}\"_\n"
            md += "\n"
        cat_q = survey.get('category_specific_questions') or []
        if cat_q:
            md += "### Category-Specific Questions\n\n"
            for q in cat_q:
                if isinstance(q, dict) and q.get('question'):
                    md += f"- \"{q['question']}\"\n"
            md += "\n"
        notes = survey.get('survey_design_notes') or {}
        if notes:
            md += "### Survey Design Notes\n\n"
            for k, v in notes.items():
                if isinstance(v, str) and v:
                    md += f"- **{k.replace('_',' ').title()}:** {v}\n"
            md += "\n"

    # A/B Test Suggestions
    ab_tests = safe_get(insight, 'ab_test_suggestions', [])
    if ab_tests and isinstance(ab_tests, list):
        md += "\n## 29. A/B Test Suggestions\n\n"
        for i, test in enumerate(ab_tests, 1):
            if isinstance(test, dict):
                md += f"{i}. **{test.get('name', test.get('test', f'Test {i}'))}**\n"
                for k, v in test.items():
                    if k not in ('name', 'test') and v:
                        md += f"   - {k.replace('_', ' ').title()}: {v}\n"
            else:
                md += f"{i}. {test}\n"
        md += "\n"

    # Thumbnail Suggestions
    thumbnails = safe_get(insight, 'thumbnail_suggestions', [])
    if thumbnails and isinstance(thumbnails, list):
        md += "\n## 30. Thumbnail Suggestions\n\n"
        for i, thumb in enumerate(thumbnails, 1):
            if isinstance(thumb, dict):
                md += f"{i}. **{thumb.get('concept', thumb.get('title', f'Thumbnail {i}'))}**\n"
                for k, v in thumb.items():
                    if k not in ('concept', 'title') and v:
                        md += f"   - {k.replace('_', ' ').title()}: {v}\n"
            else:
                md += f"{i}. {thumb}\n"
        md += "\n"

    # Landing Page Analysis
    landing_pages = safe_get(insight, 'landing_page_analysis', [])
    if landing_pages and isinstance(landing_pages, list):
        md += "\n## 31. Landing Page Analysis\n\n"
        for i, lp in enumerate(landing_pages, 1):
            if isinstance(lp, dict):
                url = lp.get('url', lp.get('page_url', ''))
                md += f"### {i}. {url or f'Page {i}'}\n\n"
                for k, v in lp.items():
                    if k not in ('url', 'page_url') and v:
                        label = k.replace('_', ' ').title()
                        if isinstance(v, list):
                            md += f"- **{label}:** {', '.join(str(x) for x in v)}\n"
                        elif isinstance(v, dict):
                            md += f"- **{label}:**\n"
                            for dk, dv in v.items():
                                if dv:
                                    md += f"  - {dk.replace('_', ' ').title()}: {dv}\n"
                        else:
                            md += f"- **{label}:** {v}\n"
                md += "\n"

    md += f"""
---

*Generated by Brand Intelligence Scraper*
*Export date: {datetime.now().strftime('%Y-%m-%d %H:%M')}*
"""

    return md
