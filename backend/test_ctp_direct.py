#!/usr/bin/env python3
"""Direct CTP test - bypasses server, calls functions directly."""
import asyncio
import sys
import os

# Load .env
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

async def main():
    from app.database import async_session as AsyncSessionLocal
    from app.models import ScrapedData, Insight, Brand, ResearchSession
    from app.services.stance_classifier import StanceClassifier
    from app.services.ctp_builder import build_ctps
    from sqlalchemy import select

    session_id = 128

    async with AsyncSessionLocal() as db:
        # Get brand info
        result = await db.execute(
            select(ResearchSession).where(ResearchSession.id == session_id)
        )
        research_session = result.scalar_one()

        result = await db.execute(
            select(Brand).where(Brand.id == research_session.brand_id)
        )
        brand = result.scalar_one()
        print(f"Brand: {brand.name} (session {session_id})")

        # Get VoC snippets
        voc_types = [
            'trustpilot', 'reddit', 'site_review', 'amazon', 'app_store',
            'google_reviews', 'forum', 'quora', 'youtube_comment',
            'g2', 'capterra', 'other_review', 'tiktok', 'instagram', 'twitter'
        ]
        result = await db.execute(
            select(ScrapedData).where(
                ScrapedData.session_id == session_id,
                ScrapedData.source_type.in_(voc_types),
                ScrapedData.content.isnot(None)
            )
        )
        items = result.scalars().all()
        print(f"VoC snippets: {len(items)}")

        # Format snippets
        snippets = []
        for item in items:
            content = item.content or ""
            if len(content.strip()) < 20:
                continue
            snippets.append({
                "id": item.id,
                "content": content[:500],
                "source_type": item.source_type,
                "source_url": item.source_url or "",
                "sentiment": item.sentiment or "",
                "sentiment_score": item.sentiment_score,
                "primary_trigger": item.primary_trigger or "",
                "blocker_type": item.blocker_type or "",
                "desired_outcome_level": item.desired_outcome_level or "",
                "proof_type_trusted": item.proof_type_trusted or "",
                "language_cues": item.language_cues or [],
                "context": item.title or brand.name
            })
        print(f"Valid snippets: {len(snippets)}")

        # Step 1: Stance classification
        print(f"\n--- STANCE CLASSIFICATION ---")
        classifier = StanceClassifier()
        classified = await classifier.classify_batch(snippets, batch_size=10)

        successful = sum(1 for s in classified if s.get("general_stance") and s["general_stance"] != "unknown")
        print(f"\nClassified: {successful}/{len(classified)}")

        # Show stance distribution
        from collections import Counter
        stances = Counter(s.get("general_stance", "unknown") for s in classified if s.get("general_stance"))
        print(f"\nStance distribution:")
        for stance, count in stances.most_common():
            pct = count / len(classified) * 100
            print(f"  {stance:25} {count:4} ({pct:.1f}%)")

        # Step 2: Build CTPs
        print(f"\n--- CTP BUILDING ---")
        result = await build_ctps(
            classified_snippets=classified,
            brand_name=brand.name,
            sector=brand.sector or "",
            vertical=brand.vertical or "",
            existing_pain_points=[],
            ad_library_data=None,
            ad_creative_patterns=None
        )

        ctps = result.get("ctps", [])
        hypothesis = result.get("hypothesis", [])
        stats = result.get("stats", {})

        print(f"\nCTPs generated: {len(ctps)}")
        for ctp in ctps:
            print(f"\n  {ctp['ctp_id']}: {ctp['ctp_name']}")
            print(f"    Stance: {ctp['general_stance']}")
            print(f"    Weight: {ctp['weight']}/10 ({ctp['review_percentage']:.0f}%)")
            print(f"    Snippets: {ctp['snippet_count']}")
            print(f"    CD6: {ctp['core_insight_general'][:100]}...")
            print(f"    Pain points: {len(ctp.get('pain_points', []))}")
            print(f"    Barriers: {len(ctp.get('barriers_objections', []))}")

        print(f"\nHypothesis entries: {len(hypothesis)}")
        print(f"Stats: {stats}")

        # Step 3: Save to DB
        print(f"\n--- SAVING TO DB ---")
        # Update stance labels on scraped data
        updated = 0
        for cd in classified:
            if cd.get("general_stance"):
                for item in items:
                    if item.id == cd.get("id"):
                        item.general_stance = cd["general_stance"]
                        item.stance_confidence = cd.get("stance_confidence")
                        updated += 1
                        break
        await db.commit()
        print(f"Updated {updated} snippets with stance labels")

        # Update insight
        result = await db.execute(
            select(Insight).where(Insight.session_id == session_id)
        )
        insight = result.scalars().first()
        if insight:
            insight.ctp_data = ctps
            insight.ctp_hypothesis = hypothesis
            insight.ctp_stats = stats
            await db.commit()
            print(f"Insight updated with CTP data")
        else:
            print(f"No insight found for session {session_id}")

        print(f"\nDONE!")

if __name__ == "__main__":
    asyncio.run(main())
