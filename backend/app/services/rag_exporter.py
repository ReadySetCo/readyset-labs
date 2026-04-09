# -*- coding: utf-8 -*-
"""
RAG-Optimized Exporter - Creates clean documents for AnythingLLM.
Exports customer reviews in a format optimized for retrieval-augmented generation.
"""

import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models import ResearchSession, ScrapedData, Brand


def clean_content_for_rag(content: str) -> str:
    """
    Clean scraped content for better RAG embeddings.
    Removes noise like Share buttons, icons, Trustpilot UI elements.
    """
    if not content:
        return ""
    
    # Remove common noise patterns
    patterns_to_remove = [
        r'!\[.*?\]\(.*?\)',  # Markdown images
        r'\[!\[.*?\].*?\]',  # Nested image links
        r'Useful\d*',  # Trustpilot useful button
        r'Share',  # Share button
        r'Verified',  # Verified badge
        r'Company replied',  # Company replied notice
        r'See more',  # See more links
        r'See all \d+[\w\s]+',  # See all X reviews
        r'Rated \d out of \d stars',  # Star ratings text
        r'TrustScore.*?stars',  # TrustScore
        r'Claimed profile',  # Profile status
        r'Write a review',  # CTA buttons
        r'Visit website',  # CTA buttons
        r'\[.*?\]\(https?://.*?\)',  # External links
        r'https?://\S+',  # Raw URLs
        r'\*\s*\*\s*\*',  # Horizontal rules
        r'---+',  # More horizontal rules
        r'^\s*-\s*$',  # Empty list items
        r'^\s*\*\s*$',  # Empty bullet points
    ]
    
    cleaned = content
    for pattern in patterns_to_remove:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE | re.MULTILINE)
    
    # Remove excessive whitespace and empty lines
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    cleaned = re.sub(r' +', ' ', cleaned)
    cleaned = cleaned.strip()
    
    return cleaned


def extract_reviews_from_content(content: str, source: str) -> List[Dict[str, str]]:
    """
    Extract individual reviews from scraped content.
    Returns list of review dicts with text and metadata.
    """
    reviews = []
    
    if not content:
        return reviews
    
    # Different extraction patterns based on source
    if source.lower() in ['trustpilot', 'reviews', 'yelp']:
        # Look for review patterns in Trustpilot-style content
        # Reviews often start with rating or title patterns
        lines = content.split('\n')
        current_review = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Skip noise lines
            if any(noise in line.lower() for noise in [
                'share', 'useful', 'verified', 'see more', 'company replied',
                'rated', 'stars', 'trustscore', 'write a review', 'visit website'
            ]):
                continue
            
            # Skip very short lines (likely UI elements)
            if len(line) < 20:
                continue
            
            # Skip lines that are mostly links or images
            if line.startswith('!') or line.startswith('['):
                continue
            
            # This looks like actual content
            current_review.append(line)
        
        # Join all valid content as one review if we couldn't separate them
        if current_review:
            full_text = ' '.join(current_review)
            # Split by sentence endings to create separate review units
            sentences = re.split(r'(?<=[.!?])\s+', full_text)
            
            # Group sentences into reviews (roughly 2-4 sentences each)
            current_chunk = []
            for sentence in sentences:
                current_chunk.append(sentence)
                if len(current_chunk) >= 3 or len(' '.join(current_chunk)) > 300:
                    reviews.append({
                        'text': ' '.join(current_chunk),
                        'source': source
                    })
                    current_chunk = []
            
            if current_chunk:
                reviews.append({
                    'text': ' '.join(current_chunk),
                    'source': source
                })
    else:
        # For other sources, just clean and use as-is
        cleaned = clean_content_for_rag(content)
        if cleaned and len(cleaned) > 50:
            reviews.append({
                'text': cleaned[:2000],  # Limit size
                'source': source
            })
    
    return reviews


class RAGExporter:
    """Exports research data optimized for RAG/AnythingLLM."""
    
    def __init__(self, output_dir: str = "knowledge_base_rag"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    async def export_session(
        self,
        db: AsyncSession,
        session_id: int
    ) -> Dict[str, Any]:
        """
        Export session data in RAG-optimized format.
        Creates clean, chunked documents ideal for embedding.
        """
        from sqlalchemy.orm import selectinload
        from ..models import Insight
        
        # Get session with relationships
        result = await db.execute(
            select(ResearchSession)
            .options(selectinload(ResearchSession.brand))
            .options(selectinload(ResearchSession.insights))
            .where(ResearchSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        
        if not session:
            return {"error": f"Session {session_id} not found"}
        
        brand = session.brand
        brand_name = brand.name if brand else f"Brand_{session_id}"
        safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in brand_name)
        
        brand_dir = self.output_dir / safe_name
        brand_dir.mkdir(parents=True, exist_ok=True)
        
        files_created = []
        total_reviews = 0
        
        # Get scraped data
        result = await db.execute(
            select(ScrapedData)
            .where(ScrapedData.session_id == session_id)
            .where(ScrapedData.content.isnot(None))
        )
        items = result.scalars().all()
        
        # Create focused reviews document
        reviews_file = brand_dir / "customer_reviews.md"
        reviews_content = f"# {brand_name} - Customer Reviews\n\n"
        reviews_content += "This document contains customer reviews and feedback.\n\n"
        
        for item in items:
            source = item.source_type or 'unknown'
            content = item.content or ''
            
            # Skip non-review sources
            if source in ['brand_website', 'competitor_comparison', 'ad_library']:
                continue
            
            cleaned = clean_content_for_rag(content)
            if cleaned and len(cleaned) > 50:
                sentiment_tag = f" ({item.sentiment})" if item.sentiment else ""
                reviews_content += f"## Review from {source.replace('_', ' ').title()}{sentiment_tag}\n\n"
                reviews_content += f"{cleaned[:1500]}\n\n"
                total_reviews += 1
        
        reviews_file.write_text(reviews_content, encoding='utf-8')
        files_created.append(reviews_file)
        
        # Create insights summary (if available)
        if session.insights:
            insight = session.insights[-1] if isinstance(session.insights, list) else session.insights
            
            insights_file = brand_dir / "brand_insights.md"
            insights_content = f"# {brand_name} - Key Insights\n\n"
            
            if hasattr(insight, 'pain_points') and insight.pain_points:
                insights_content += "## Customer Pain Points\n"
                for pp in insight.pain_points[:10]:
                    insights_content += f"- {pp}\n"
                insights_content += "\n"
            
            if hasattr(insight, 'value_props') and insight.value_props:
                insights_content += "## Value Propositions\n"
                for vp in insight.value_props[:10]:
                    insights_content += f"- {vp}\n"
                insights_content += "\n"
            
            if hasattr(insight, 'icps') and insight.icps:
                insights_content += "## Ideal Customer Profiles\n"
                for icp in insight.icps[:5]:
                    if isinstance(icp, dict):
                        name = icp.get('name', 'Unknown')
                        desc = icp.get('description', '')
                        insights_content += f"### {name}\n{desc}\n\n"
                    else:
                        insights_content += f"- {icp}\n"
                insights_content += "\n"
            
            if hasattr(insight, 'verbatim_quotes') and insight.verbatim_quotes:
                insights_content += "## Verbatim Customer Quotes\n"
                for q in insight.verbatim_quotes[:15]:
                    if isinstance(q, dict):
                        quote = q.get('quote', str(q))
                        insights_content += f"> \"{quote}\"\n\n"
                    else:
                        insights_content += f"> \"{q}\"\n\n"
            
            insights_file.write_text(insights_content, encoding='utf-8')
            files_created.append(insights_file)
        
        # Brand overview
        if brand:
            overview_file = brand_dir / "brand_overview.md"
            overview_content = f"""# {brand_name}

**Website**: {brand.website_url or 'N/A'}
**Sector**: {brand.sector or 'N/A'}
**Description**: {brand.description or 'N/A'}
**Target Audience**: {brand.target_audience or 'N/A'}
"""
            overview_file.write_text(overview_content, encoding='utf-8')
            files_created.append(overview_file)
        
        return {
            "session_id": session_id,
            "brand_name": brand_name,
            "output_dir": str(brand_dir),
            "files_created": [str(f) for f in files_created],
            "total_files": len(files_created),
            "total_reviews": total_reviews,
            "exported_at": datetime.now().isoformat()
        }


# Singleton
_rag_exporter: Optional[RAGExporter] = None

def get_rag_exporter(output_dir: str = "knowledge_base_rag") -> RAGExporter:
    global _rag_exporter
    if _rag_exporter is None:
        _rag_exporter = RAGExporter(output_dir)
    return _rag_exporter
