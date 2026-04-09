"""
Quality Auditor - Phase 9

Verifica que el contenido generado (scripts, ICPs, hooks) 
refleja correctamente los datos scrapeados.

Objetivos:
1. Verificar que scripts usan verbatim quotes reales
2. Verificar que pain points son de la data
3. Detectar contenido genérico vs específico
4. Medir cobertura de data usada
"""

from typing import Dict, Any, List, Tuple
from datetime import datetime, timezone
from collections import defaultdict
import re


class QualityAuditor:
    """
    Audits generated content against source data.
    
    Checks:
    - Verbatim quotes match source data
    - Pain points are from scraped data
    - ICPs reflect real customer segments
    - Hooks match video analysis patterns
    """
    
    def audit_scripts(
        self,
        scripts: List[Dict[str, Any]],
        source_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Audit generated scripts against source data.
        
        Args:
            scripts: Generated scripts
            source_data: Unified data layer or raw data
            
        Returns:
            Audit report with scores and issues
        """
        if not scripts:
            return {"score": 0, "issues": ["No scripts to audit"]}
        
        # Extract source references
        verbatims = self._extract_verbatims(source_data)
        pain_points = self._extract_pain_points(source_data)
        frameworks = self._extract_frameworks(source_data)
        
        issues = []
        scores = []
        script_audits = []
        
        for i, script in enumerate(scripts):
            audit = self._audit_single_script(
                script, verbatims, pain_points, frameworks
            )
            script_audits.append({
                "script_name": script.get("script_name", f"Script {i+1}"),
                **audit
            })
            scores.append(audit["score"])
            issues.extend(audit["issues"])
        
        avg_score = sum(scores) / len(scores) if scores else 0
        
        return {
            "score": round(avg_score, 1),
            "total_scripts": len(scripts),
            "scripts_with_verbatims": sum(1 for a in script_audits if a["has_verbatims"]),
            "scripts_with_pain_points": sum(1 for a in script_audits if a["has_pain_points"]),
            "script_audits": script_audits,
            "issues": issues[:10],  # Top 10 issues
            "recommendations": self._generate_recommendations(script_audits),
        }
    
    def _audit_single_script(
        self,
        script: Dict[str, Any],
        verbatims: List[str],
        pain_points: List[str],
        frameworks: List[str],
    ) -> Dict[str, Any]:
        """Audit a single script."""
        issues = []
        score_components = []
        
        # Check for verbatim usage
        based_on_verbatims = script.get("based_on_verbatims", [])
        has_verbatims = len(based_on_verbatims) > 0
        
        if has_verbatims:
            # Verify verbatims are real
            verified_verbatims = []
            for v in based_on_verbatims:
                if self._find_match(v, verbatims):
                    verified_verbatims.append(v)
                else:
                    issues.append(f"Verbatim not found in source: '{v[:50]}...'")
            
            verbatim_score = len(verified_verbatims) / len(based_on_verbatims) * 100
            score_components.append(verbatim_score)
        else:
            issues.append("Script has no verbatim quotes")
            score_components.append(0)
        
        # Check for pain points
        pain_points_addressed = script.get("pain_points_addressed", [])
        has_pain_points = len(pain_points_addressed) > 0
        
        if has_pain_points:
            verified_pains = []
            for pp in pain_points_addressed:
                if self._find_match(pp, pain_points):
                    verified_pains.append(pp)
            
            pain_score = len(verified_pains) / len(pain_points_addressed) * 100
            score_components.append(pain_score)
        else:
            issues.append("Script has no pain points")
            score_components.append(50)  # Neutral
        
        # Check framework
        framework = script.get("framework", "")
        has_valid_framework = framework in frameworks or len(frameworks) == 0
        
        if not has_valid_framework and frameworks:
            issues.append(f"Framework '{framework}' not in source patterns")
            score_components.append(50)
        else:
            score_components.append(100)
        
        # Check for generic content indicators
        full_script = script.get("full_script", "")
        generic_score = self._check_generic_content(full_script)
        score_components.append(generic_score)
        
        if generic_score < 50:
            issues.append("Script may contain generic/placeholder content")
        
        avg_score = sum(score_components) / len(score_components) if score_components else 0
        
        return {
            "score": round(avg_score, 1),
            "has_verbatims": has_verbatims,
            "has_pain_points": has_pain_points,
            "has_valid_framework": has_valid_framework,
            "issues": issues,
        }
    
    def _find_match(self, needle: str, haystack: List[str], threshold: float = 0.5) -> bool:
        """Check if needle exists in haystack (fuzzy match)."""
        needle_lower = needle.lower().strip()
        
        for item in haystack:
            item_lower = item.lower().strip()
            
            # Exact or substring match
            if needle_lower in item_lower or item_lower in needle_lower:
                return True
            
            # Word overlap
            needle_words = set(needle_lower.split())
            item_words = set(item_lower.split())
            
            if len(needle_words) > 2 and len(item_words) > 2:
                overlap = len(needle_words & item_words)
                overlap_ratio = overlap / min(len(needle_words), len(item_words))
                if overlap_ratio >= threshold:
                    return True
        
        return False
    
    def _check_generic_content(self, text: str) -> int:
        """Check for generic/placeholder content. Returns score 0-100."""
        if not text:
            return 0
        
        # Generic indicators
        generic_patterns = [
            r'\[INSERT\s+',
            r'\[YOUR\s+',
            r'\[BRAND\]',
            r'\[PRODUCT\]',
            r'Lorem ipsum',
            r'placeholder',
            r'example\.com',
            r'TODO:',
        ]
        
        text_lower = text.lower()
        generic_count = 0
        
        for pattern in generic_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                generic_count += 1
        
        # Score: 100 = no generic, 0 = very generic
        score = max(0, 100 - (generic_count * 25))
        return score
    
    def _extract_verbatims(self, source_data: Dict[str, Any]) -> List[str]:
        """Extract verbatim quotes from source data."""
        verbatims = []
        
        # From insights
        if "verbatim_quotes" in source_data:
            for v in source_data["verbatim_quotes"]:
                if isinstance(v, dict):
                    verbatims.append(v.get("quote", ""))
                else:
                    verbatims.append(str(v))
        
        # From voc section
        if "voc" in source_data:
            voc = source_data["voc"]
            for v in voc.get("verbatim_quotes", []):
                if isinstance(v, dict):
                    verbatims.append(v.get("quote", ""))
                else:
                    verbatims.append(str(v))
        
        # From scraped data content
        if "scraped_data" in source_data:
            for item in source_data.get("scraped_data", [])[:50]:
                content = item.get("content", "")
                if content and len(content) > 20:
                    verbatims.append(content)
        
        return [v for v in verbatims if v]
    
    def _extract_pain_points(self, source_data: Dict[str, Any]) -> List[str]:
        """Extract pain points from source data."""
        pain_points = []
        
        # Direct pain points
        pain_points.extend(source_data.get("pain_points", []))
        
        # Market pain points
        pain_points.extend(source_data.get("market_pain_points", []))
        
        # From computed section
        if "computed" in source_data:
            pain_points.extend(source_data["computed"].get("pain_points", []))
        
        return [pp for pp in pain_points if pp]
    
    def _extract_frameworks(self, source_data: Dict[str, Any]) -> List[str]:
        """Extract frameworks from source data."""
        frameworks = []
        
        # From video intelligence
        if "video_intelligence" in source_data:
            vi = source_data["video_intelligence"]
            frameworks.extend(vi.get("frameworks", {}).keys())
        
        # From ad patterns
        if "ad_creative_patterns" in source_data:
            patterns = source_data["ad_creative_patterns"]
            frameworks.extend(patterns.get("frameworks", {}).keys())
        
        return list(set(frameworks))
    
    def _generate_recommendations(
        self, 
        script_audits: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate recommendations based on audit results."""
        recommendations = []
        
        # Count issues
        no_verbatim_count = sum(1 for a in script_audits if not a["has_verbatims"])
        no_pain_count = sum(1 for a in script_audits if not a["has_pain_points"])
        low_score_count = sum(1 for a in script_audits if a["score"] < 50)
        
        if no_verbatim_count > len(script_audits) / 2:
            recommendations.append(
                "Most scripts lack verbatim quotes. Consider re-running generator with more source data."
            )
        
        if no_pain_count > len(script_audits) / 2:
            recommendations.append(
                "Most scripts don't address specific pain points. Ensure insights contain pain_points."
            )
        
        if low_score_count > 0:
            recommendations.append(
                f"{low_score_count} scripts scored below 50%. Review and regenerate."
            )
        
        if not recommendations:
            recommendations.append("Scripts appear well-grounded in source data. OK")
        
        return recommendations
    
    def audit_icps(
        self,
        icps: List[Dict[str, Any]],
        source_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Audit generated ICPs against source data."""
        if not icps:
            return {"score": 0, "issues": ["No ICPs to audit"]}
        
        # Check if ICPs have characteristics from data
        customer_language = source_data.get("customer_language", [])
        pain_points = self._extract_pain_points(source_data)
        
        scores = []
        issues = []
        
        for icp in icps:
            characteristics = icp.get("characteristics", [])
            has_grounded_chars = any(
                self._find_match(c, customer_language + pain_points)
                for c in characteristics
            )
            
            if has_grounded_chars:
                scores.append(80)
            else:
                scores.append(40)
                issues.append(f"ICP '{icp.get('name')}' characteristics seem generic")
        
        return {
            "score": round(sum(scores) / len(scores), 1) if scores else 0,
            "total_icps": len(icps),
            "issues": issues,
        }
    
    def generate_audit_report(
        self,
        scripts: List[Dict[str, Any]] = None,
        icps: List[Dict[str, Any]] = None,
        source_data: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Generate comprehensive audit report."""
        source_data = source_data or {}
        
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "overall_score": 0,
            "audits": {},
        }
        
        scores = []
        
        # Audit scripts
        if scripts:
            script_audit = self.audit_scripts(scripts, source_data)
            report["audits"]["scripts"] = script_audit
            scores.append(script_audit["score"])
        
        # Audit ICPs
        if icps:
            icp_audit = self.audit_icps(icps, source_data)
            report["audits"]["icps"] = icp_audit
            scores.append(icp_audit["score"])
        
        # Overall score
        report["overall_score"] = round(sum(scores) / len(scores), 1) if scores else 0
        
        # Quality grade
        score = report["overall_score"]
        if score >= 80:
            report["grade"] = "A"
            report["summary"] = "Content is well-grounded in source data"
        elif score >= 60:
            report["grade"] = "B"
            report["summary"] = "Content mostly uses source data with some gaps"
        elif score >= 40:
            report["grade"] = "C"
            report["summary"] = "Content has moderate data grounding, needs improvement"
        else:
            report["grade"] = "D"
            report["summary"] = "Content appears generic, regenerate with more data"
        
        return report


# Convenience function
def audit_generated_content(
    scripts: List[Dict[str, Any]] = None,
    icps: List[Dict[str, Any]] = None,
    source_data: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """Convenience function for quick audit."""
    return QualityAuditor().generate_audit_report(scripts, icps, source_data)
