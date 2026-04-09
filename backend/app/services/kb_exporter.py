# -*- coding: utf-8 -*-
"""
Knowledge Base Exporter - Exports research data to files for Open WebUI RAG.
Creates structured documents that Open WebUI can ingest as a knowledge base.
"""

import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models import ResearchSession, ScrapedData, Brand


class KnowledgeBaseExporter:
    """Exports research data to knowledge base files for RAG."""
    
    def __init__(self, output_dir: str = "knowledge_base"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    async def export_session(
        self,
        db: AsyncSession,
        session_id: int
    ) -> Dict[str, Any]:
        """
        Export a research session to knowledge base files.
        Creates structured documents for Open WebUI to ingest.
        
        Returns: dict with export stats and file paths
        """
        from sqlalchemy.orm import selectinload
        from ..models import Insight
        
        # Get session data with relationships
        result = await db.execute(
            select(ResearchSession)
            .options(selectinload(ResearchSession.brand))
            .options(selectinload(ResearchSession.insights))
            .where(ResearchSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        
        if not session:
            return {"error": f"Session {session_id} not found"}
        
        # Get brand info from related Brand object
        brand = session.brand
        brand_info = {}
        if brand:
            brand_info = {
                'name': brand.name,
                'website_url': brand.website_url,
                'description': brand.description,
                'sector': brand.sector,
                'vertical': brand.vertical,
                'tagline': brand.tagline,
                'brand_values': brand.brand_values,
                'brand_aesthetic': brand.brand_aesthetic,
                'tone_of_voice': brand.tone_of_voice,
                'target_audience': brand.target_audience,
                'products': brand.products,
            }
        
        # Get insights from related Insight objects
        insights = {}
        if session.insights:
            # Take the most recent insight
            insight = session.insights[-1] if isinstance(session.insights, list) else session.insights
            if hasattr(insight, 'pain_points'):
                insights = {
                    'pain_points': insight.pain_points or [],
                    'value_props': insight.value_props or [],
                    'icps': insight.icps or [],
                    'objections': insight.objections or [],
                    'messaging_angles': insight.messaging_angles or [],
                    'recommended_hooks': insight.recommended_hooks or [],
                    'verbatim_quotes': getattr(insight, 'verbatim_quotes', []) or [],
                }
        
        brand_name = brand_info.get('name', f'Brand_{session_id}')
        safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in brand_name)
        
        # Create brand directory
        brand_dir = self.output_dir / safe_name
        brand_dir.mkdir(parents=True, exist_ok=True)
        
        files_created = []
        
        # 1. Export Brand Overview
        overview_file = await self._export_brand_overview(brand_dir, brand_info, insights, session)
        files_created.append(overview_file)
        
        # 2. Export Insights Summary
        if insights:
            insights_file = await self._export_insights(brand_dir, brand_name, insights)
            files_created.append(insights_file)
        
        # 3. Export Scraped Data by Source
        scraped_files = await self._export_scraped_data(db, brand_dir, session_id, brand_name)
        files_created.extend(scraped_files)
        
        # 4. Export Ad Library Data (CRITICAL - was missing from RAG!)
        if session.insights:
            insight = session.insights[-1] if isinstance(session.insights, list) else session.insights
            ad_lib_file = await self._export_ad_library_data(brand_dir, brand_name, insight)
            if ad_lib_file:
                files_created.append(ad_lib_file)
        
        # 5. Create combined knowledge file
        combined_file = await self._create_combined_file(brand_dir, brand_name, files_created)
        files_created.append(combined_file)
        
        return {
            "session_id": session_id,
            "brand_name": brand_name,
            "output_dir": str(brand_dir),
            "files_created": [str(f) for f in files_created],
            "total_files": len(files_created),
            "exported_at": datetime.now().isoformat()
        }
    
    async def _export_brand_overview(
        self,
        brand_dir: Path,
        brand_info: Dict,
        insights: Dict,
        session: ResearchSession
    ) -> Path:
        """Export brand overview document."""
        file_path = brand_dir / "01_brand_overview.md"
        
        content = f"""# {brand_info.get('name', 'Unknown Brand')} - Brand Overview

## Basic Information
- **Name**: {brand_info.get('name', 'N/A')}
- **Website**: {brand_info.get('website_url', brand_info.get('website', 'N/A'))}
- **Sector**: {brand_info.get('sector', 'N/A')}
- **Vertical**: {brand_info.get('vertical', 'N/A')}

## Description
{brand_info.get('description', 'No description available.')}

## Tagline
{brand_info.get('tagline', 'N/A')}

## Brand Values
{self._format_list(brand_info.get('brand_values', []))}

## Brand Aesthetic
{self._format_list(brand_info.get('brand_aesthetic', []))}

## Tone of Voice
{self._format_list(brand_info.get('tone_of_voice', []))}

## Target Audience
{brand_info.get('target_audience', 'N/A')}

## Products/Services
{self._format_products(brand_info.get('products', brand_info.get('product_descriptions', [])))}

---
*Exported: {datetime.now().strftime('%Y-%m-%d %H:%M')}*
"""
        
        file_path.write_text(content, encoding='utf-8')
        return file_path
    
    async def _export_insights(
        self,
        brand_dir: Path,
        brand_name: str,
        insights: Dict
    ) -> Path:
        """Export insights document."""
        file_path = brand_dir / "02_insights.md"
        
        content = f"""# {brand_name} - Research Insights

## Pain Points
{self._format_list(insights.get('pain_points', []))}

## Value Propositions
{self._format_list(insights.get('value_props', []))}

## Ideal Customer Profiles (ICPs)
{self._format_icps(insights.get('icps', []))}

## Common Objections
{self._format_objections(insights.get('objections', []))}

## Messaging Angles
{self._format_angles(insights.get('messaging_angles', []))}

## Recommended Hooks
{self._format_list(insights.get('recommended_hooks', []))}

## Verbatim Quotes
{self._format_verbatims(insights.get('verbatim_quotes', []))}

---
*Exported: {datetime.now().strftime('%Y-%m-%d %H:%M')}*
"""
        
        file_path.write_text(content, encoding='utf-8')
        return file_path
    
    async def _export_scraped_data(
        self,
        db: AsyncSession,
        brand_dir: Path,
        session_id: int,
        brand_name: str
    ) -> List[Path]:
        """Export scraped data grouped by source."""
        result = await db.execute(
            select(ScrapedData)
            .where(ScrapedData.session_id == session_id)
            .where(ScrapedData.content.isnot(None))
        )
        items = result.scalars().all()
        
        # Group by source
        by_source: Dict[str, List] = {}
        for item in items:
            source = item.source_type or 'unknown'
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(item)
        
        files = []
        for idx, (source, source_items) in enumerate(sorted(by_source.items()), start=3):
            file_path = brand_dir / f"{idx:02d}_{source}_feedback.md"
            
            content = f"""# {brand_name} - {source.title()} Customer Feedback

Total items: {len(source_items)}

"""
            for item in source_items[:100]:  # Limit to 100 per source
                sentiment = f" [{item.sentiment}]" if item.sentiment else ""
                author = f" by @{item.author}" if item.author else ""
                likes = f" | {item.likes} likes" if item.likes else ""
                
                content += f"""---

### {item.title or 'Feedback'}{sentiment}{author}{likes}

{item.content or 'No content'}

"""
            
            file_path.write_text(content, encoding='utf-8')
            files.append(file_path)
        
        return files
    
    async def _export_ad_library_data(
        self,
        brand_dir: Path,
        brand_name: str,
        insight
    ) -> Optional[Path]:
        """Export Ad Library data to knowledge base for RAG search."""
        # Get ad library data from insight
        ad_library_data = getattr(insight, 'ad_library_data', None)
        ad_patterns = getattr(insight, 'ad_creative_patterns', None)
        
        if not ad_library_data and not ad_patterns:
            return None
        
        file_path = brand_dir / "50_ad_library_analysis.md"
        
        content = f"""# {brand_name} - Ad Library Analysis

## Overview
This document contains analyzed ads from Meta Ad Library for {brand_name}.
These ads were analyzed using Gemini Vision to extract creative patterns.

"""
        
        # Add patterns summary
        if ad_patterns and isinstance(ad_patterns, dict):
            content += """## Creative Patterns Summary

### Frameworks Used
"""
            frameworks = ad_patterns.get("frameworks", {})
            if frameworks:
                for fw, count in list(frameworks.items())[:10]:
                    content += f"- **{fw}**: {count} ads\n"
            else:
                content += "- No framework data available\n"
            
            content += """
### Hook Types
"""
            hook_types = ad_patterns.get("hook_types", {})
            if hook_types:
                for ht, count in list(hook_types.items())[:10]:
                    content += f"- **{ht}**: {count} ads\n"
            
            content += """
### Emotions Targeted
"""
            emotions = ad_patterns.get("emotions", {})
            if emotions:
                for em, count in list(emotions.items())[:10]:
                    content += f"- **{em}**: {count} ads\n"
            
            # Add transcriptions
            content += """
## Top Ad Transcriptions & Scripts

"""
            transcriptions = ad_patterns.get("top_transcriptions", [])
            for i, trans in enumerate(transcriptions[:10], 1):
                if isinstance(trans, dict):
                    text = trans.get("text", "")[:500]
                    hook_strength = trans.get("hook_strength", "N/A")
                    effectiveness = trans.get("effectiveness", "N/A")
                    content += f"""### Ad #{i}
- **Hook Strength**: {hook_strength}/5
- **Effectiveness**: {effectiveness}/5

**Transcription:**
> {text}

---

"""
        
        # Add individual ad data
        if ad_library_data and isinstance(ad_library_data, dict):
            ads = ad_library_data.get("ads", [])
            if ads:
                content += f"""
## Individual Ads Analyzed ({len(ads)} total)

"""
                for i, ad in enumerate(ads[:20], 1):
                    if isinstance(ad, dict):
                        library_id = ad.get("library_id", f"ad_{i}")
                        ad_copy = ad.get("ad_copy", "")[:300]
                        cta = ad.get("cta", "N/A")
                        platforms = ", ".join(ad.get("platforms", ["Unknown"]))
                        
                        analysis = ad.get("creative_analysis", {})
                        framework = analysis.get("framework", "N/A") if analysis else "N/A"
                        hook = analysis.get("opening_copy", "")[:100] if analysis else ""
                        
                        content += f"""### Ad: {library_id}
- **Framework**: {framework}
- **CTA**: {cta}
- **Platforms**: {platforms}

**Ad Copy:**
{ad_copy or "No copy available"}

**Hook:**
> {hook or "N/A"}

---

"""
        
        content += f"""
---
*Exported: {datetime.now().strftime('%Y-%m-%d %H:%M')}*
"""
        
        file_path.write_text(content, encoding='utf-8')
        return file_path
    
    async def _create_combined_file(
        self,
        brand_dir: Path,
        brand_name: str,
        files: List[Path]
    ) -> Path:
        """Create a combined knowledge file for easy import."""
        file_path = brand_dir / "00_COMBINED_KNOWLEDGE.md"
        
        content = f"""# {brand_name} - Complete Research Knowledge Base

*This file combines all research data for {brand_name}.*

"""
        
        for f in sorted(files):
            if f.name != "00_COMBINED_KNOWLEDGE.md":
                try:
                    file_content = f.read_text(encoding='utf-8')
                    content += f"\n\n{'='*80}\n\n"
                    content += file_content
                except Exception as e:
                    content += f"\n\n[Error reading {f.name}: {e}]\n\n"
        
        file_path.write_text(content, encoding='utf-8')
        return file_path
    
    # Helper formatting methods
    def _format_list(self, items: List) -> str:
        if not items:
            return "- None identified"
        return "\n".join(f"- {item}" for item in items[:20])
    
    def _format_products(self, products: List) -> str:
        if not products:
            return "- No products listed"
        result = []
        for p in products[:10]:
            if isinstance(p, dict):
                name = p.get('name', 'Unknown')
                desc = p.get('description', '')
                result.append(f"- **{name}**: {desc[:100]}")
            else:
                result.append(f"- {p}")
        return "\n".join(result)
    
    def _format_icps(self, icps: List) -> str:
        if not icps:
            return "No ICPs identified."
        result = []
        for icp in icps[:5]:
            if isinstance(icp, dict):
                name = icp.get('name', 'Unknown')
                desc = icp.get('description', '')
                pain = ", ".join(icp.get('pain_points', [])[:3])
                result.append(f"""### {name}
{desc}

**Pain Points**: {pain or 'N/A'}
""")
            else:
                result.append(f"- {icp}")
        return "\n".join(result)
    
    def _format_objections(self, objections: List) -> str:
        if not objections:
            return "- No objections identified"
        result = []
        for obj in objections[:10]:
            if isinstance(obj, dict):
                text = obj.get('objection', str(obj))
                freq = obj.get('frequency', '')
                counter = obj.get('counter_messaging', '')
                result.append(f"- **{text}**")
                if freq:
                    result.append(f"  - Frequency: {freq}")
                if counter:
                    result.append(f"  - Counter: {counter}")
            else:
                result.append(f"- {obj}")
        return "\n".join(result)
    
    def _format_angles(self, angles: List) -> str:
        if not angles:
            return "- No messaging angles identified"
        result = []
        for angle in angles[:10]:
            if isinstance(angle, dict):
                name = angle.get('name', 'Unknown')
                hook = angle.get('hook', '')
                desc = angle.get('description', '')
                result.append(f"### {name}")
                if hook:
                    result.append(f"**Hook**: {hook}")
                if desc:
                    result.append(f"{desc}")
                result.append("")
            else:
                result.append(f"- {angle}")
        return "\n".join(result)
    
    def _format_verbatims(self, quotes: List) -> str:
        if not quotes:
            return "- No verbatim quotes collected"
        result = []
        for q in quotes[:20]:
            if isinstance(q, dict):
                quote = q.get('quote', str(q))
                context = q.get('context', '')
                result.append(f'> "{quote}"')
                if context:
                    result.append(f"  *Context: {context}*")
                result.append("")
            else:
                result.append(f'> "{q}"')
        return "\n".join(result)


# Singleton instance
_exporter: Optional[KnowledgeBaseExporter] = None

def get_kb_exporter(output_dir: str = "knowledge_base") -> KnowledgeBaseExporter:
    global _exporter
    if _exporter is None:
        _exporter = KnowledgeBaseExporter(output_dir)
    return _exporter
