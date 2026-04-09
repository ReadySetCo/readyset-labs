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

    md += f"""
---

*Generated by Brand Intelligence Scraper*
*Export date: {datetime.now().strftime('%Y-%m-%d %H:%M')}*
"""

    return md
