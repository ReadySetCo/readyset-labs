"""
Proto-ICP Builder - Clusters classified snippets by Trigger × Blocker.
Produces actionable ICP candidates from Voice of Customer data.
"""

from collections import defaultdict, Counter
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import json


@dataclass
class ProtoICPCluster:
    """A cluster of snippets sharing the same Trigger × Blocker pattern."""
    cluster_id: str
    trigger_label: str
    blocker_label: str
    snippet_count: int
    top_phrases: List[str]  # Language cues
    outcome_distribution: Dict[str, int]  # functional/emotional/identity counts
    proof_type_distribution: Dict[str, int]  # proof type counts
    representative_snippets: List[Dict[str, Any]]  # 3-5 best examples with URLs
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ProtoICPBuilder:
    """
    Builds Proto-ICPs from classified VoC snippets.
    
    Core mechanism: Groups snippets by (Primary Trigger × Primary Blocker)
    to identify distinct customer segments with unique motivations.
    """
    
    def __init__(self):
        self.min_cluster_size = 1  # Allow single-snippet clusters for sparse data
        self.max_representative_snippets = 5
        self.max_phrases = 10
    
    def build_clusters(
        self, 
        classified_snippets: List[Dict[str, Any]]
    ) -> List[ProtoICPCluster]:
        """
        Build Proto-ICP clusters from classified snippets.
        
        Args:
            classified_snippets: List of snippets with classification tags:
                - primary_trigger
                - blocker_type (friction/objection)
                - desired_outcome (functional/emotional/identity)
                - proof_type_trusted
                - language_cues
                - source_url
                - content
                
        Returns:
            List of ProtoICPCluster sorted by snippet_count (largest first)
        """
        if not classified_snippets:
            return []
        
        # Group by Trigger × Blocker
        clusters_data = defaultdict(list)
        
        for snippet in classified_snippets:
            classification = snippet.get("classification", snippet)
            
            trigger = classification.get("primary_trigger", "unknown")
            blocker = classification.get("blocker_type", "unknown")
            
            if trigger and blocker:
                key = f"{trigger}|{blocker}"
                clusters_data[key].append(snippet)
        
        # Build cluster objects
        clusters = []
        cluster_id = 0
        
        for key, snippets in clusters_data.items():
            if len(snippets) < self.min_cluster_size:
                continue
            
            trigger, blocker = key.split("|")
            cluster_id += 1
            
            cluster = self._build_cluster(
                cluster_id=f"ICP-{cluster_id:02d}",
                trigger_label=trigger,
                blocker_label=blocker,
                snippets=snippets
            )
            clusters.append(cluster)
        
        # Sort by size (largest first)
        clusters.sort(key=lambda c: c.snippet_count, reverse=True)
        
        return clusters
    
    def _build_cluster(
        self,
        cluster_id: str,
        trigger_label: str,
        blocker_label: str,
        snippets: List[Dict[str, Any]]
    ) -> ProtoICPCluster:
        """Build a single cluster from grouped snippets."""
        
        # Collect all language cues
        all_phrases = []
        outcomes = Counter()
        proof_types = Counter()
        
        for snippet in snippets:
            classification = snippet.get("classification", snippet)
            
            # Language cues
            cues = classification.get("language_cues", [])
            if isinstance(cues, list):
                all_phrases.extend(cues)
            
            # Outcome distribution - try both field names for compatibility
            outcome = classification.get("desired_outcome_level") or classification.get("desired_outcome", "unknown")
            if outcome:
                outcomes[outcome] += 1
            
            # Proof type distribution
            proof = classification.get("proof_type_trusted", "unknown")
            if proof:
                proof_types[proof] += 1
        
        # Get top phrases by frequency
        phrase_counts = Counter(all_phrases)
        top_phrases = [phrase for phrase, _ in phrase_counts.most_common(self.max_phrases)]
        
        # Select representative snippets (prioritize those with URLs and high confidence)
        scored_snippets = []
        for snippet in snippets:
            score = 0
            if snippet.get("source_url"):
                score += 2
            classification = snippet.get("classification", snippet)
            confidence = classification.get("confidence", 0.5)
            score += confidence
            scored_snippets.append((score, snippet))
        
        scored_snippets.sort(key=lambda x: x[0], reverse=True)
        representative = [s[1] for s in scored_snippets[:self.max_representative_snippets]]
        
        # Format representative snippets for output
        formatted_snippets = []
        for s in representative:
            formatted_snippets.append({
                "content": s.get("content", "")[:300],  # Truncate long content
                "source_type": s.get("source_type", "unknown"),
                "source_url": s.get("source_url", ""),
                "language_cues": s.get("classification", {}).get("language_cues", [])
            })
        
        return ProtoICPCluster(
            cluster_id=cluster_id,
            trigger_label=trigger_label,
            blocker_label=blocker_label,
            snippet_count=len(snippets),
            top_phrases=top_phrases,
            outcome_distribution=dict(outcomes),
            proof_type_distribution=dict(proof_types),
            representative_snippets=formatted_snippets
        )
    
    def recommend_top_icps(
        self, 
        clusters: List[ProtoICPCluster],
        top_n: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Recommend top N ICPs based on scoring criteria.
        
        Scoring:
        - Frequency (cluster size)
        - Distinctiveness (unique blocker/proof type)
        - Evidence quality (snippets with URLs)
        """
        if not clusters:
            return []
        
        scored = []
        
        for cluster in clusters:
            score = 0
            rationale = []
            risks = []
            
            # Frequency score (normalized by max)
            max_size = max(c.snippet_count for c in clusters)
            freq_score = cluster.snippet_count / max_size * 40
            score += freq_score
            if cluster.snippet_count >= 5:
                rationale.append(f"High volume ({cluster.snippet_count} snippets)")
            
            # Evidence quality (snippets with URLs)
            urls_count = sum(1 for s in cluster.representative_snippets if s.get("source_url"))
            evidence_score = (urls_count / len(cluster.representative_snippets)) * 30 if cluster.representative_snippets else 0
            score += evidence_score
            if urls_count >= 3:
                rationale.append("Strong evidence with source URLs")
            else:
                risks.append("Limited traceable evidence")
            
            # Distinctiveness (variety in proof types)
            distinct_proofs = len(cluster.proof_type_distribution)
            if distinct_proofs >= 2:
                score += 15
                rationale.append("Multiple proof types resonate")
            
            # Clear trigger/blocker
            if cluster.trigger_label != "unknown" and cluster.blocker_label != "unknown":
                score += 15
                rationale.append(f"Clear pattern: {cluster.trigger_label} → {cluster.blocker_label}")
            else:
                risks.append("Unclear trigger or blocker pattern")
            
            scored.append({
                "cluster": cluster.to_dict(),
                "score": round(score, 1),
                "rationale": " | ".join(rationale) if rationale else "Moderate signals",
                "risks": " | ".join(risks) if risks else "None identified"
            })
        
        # Sort by score
        scored.sort(key=lambda x: x["score"], reverse=True)
        
        return scored[:top_n]
    
    def generate_report(
        self, 
        clusters: List[ProtoICPCluster],
        brand_name: str = "Brand"
    ) -> str:
        """Generate markdown report of Proto-ICPs."""
        
        lines = [
            f"# Proto-ICP Report: {brand_name}",
            "",
            f"**Total Clusters:** {len(clusters)}",
            f"**Total Snippets Analyzed:** {sum(c.snippet_count for c in clusters)}",
            "",
            "---",
            ""
        ]
        
        # Recommendations
        recommendations = self.recommend_top_icps(clusters)
        if recommendations:
            lines.append("## 🎯 Recommended ICPs to Start")
            lines.append("")
            for i, rec in enumerate(recommendations, 1):
                cluster = rec["cluster"]
                lines.append(f"### {i}. {cluster['cluster_id']}: {cluster['trigger_label']} × {cluster['blocker_label']}")
                lines.append(f"- **Score:** {rec['score']}")
                lines.append(f"- **Snippets:** {cluster['snippet_count']}")
                lines.append(f"- **Rationale:** {rec['rationale']}")
                lines.append(f"- **Risks:** {rec['risks']}")
                lines.append("")
        
        lines.append("---")
        lines.append("")
        lines.append("## All Clusters")
        lines.append("")
        
        for cluster in clusters:
            lines.append(f"### {cluster.cluster_id}: {cluster.trigger_label} × {cluster.blocker_label}")
            lines.append(f"**Snippets:** {cluster.snippet_count}")
            lines.append("")
            
            # Distributions
            if cluster.outcome_distribution:
                lines.append(f"**Outcome Distribution:** {cluster.outcome_distribution}")
            if cluster.proof_type_distribution:
                lines.append(f"**Proof Types:** {cluster.proof_type_distribution}")
            
            # Top phrases
            if cluster.top_phrases:
                lines.append(f"**Language Cues:** {', '.join(cluster.top_phrases[:5])}")
            
            lines.append("")
            
            # Representative snippets
            lines.append("**Representative Snippets:**")
            for j, snippet in enumerate(cluster.representative_snippets[:3], 1):
                content = snippet.get("content", "")[:150]
                source = snippet.get("source_type", "")
                url = snippet.get("source_url", "")
                lines.append(f'{j}. "{content}..."')
                if url:
                    lines.append(f"   - Source: [{source}]({url})")
                else:
                    lines.append(f"   - Source: {source}")
            
            lines.append("")
            lines.append("---")
            lines.append("")
        
        return "\n".join(lines)
    
    def to_json(self, clusters: List[ProtoICPCluster]) -> str:
        """Export clusters as JSON."""
        return json.dumps(
            [c.to_dict() for c in clusters],
            indent=2,
            ensure_ascii=False
        )


# Convenience function
def build_proto_icps(
    classified_snippets: List[Dict[str, Any]],
    brand_name: str = "Brand"
) -> Dict[str, Any]:
    """
    Build Proto-ICPs from classified snippets and return full output.
    
    Returns:
        Dict with:
        - clusters: List of cluster dicts
        - recommendations: Top 3 recommended ICPs
        - report: Markdown report
        - stats: Summary statistics
    """
    builder = ProtoICPBuilder()
    clusters = builder.build_clusters(classified_snippets)
    
    return {
        "clusters": [c.to_dict() for c in clusters],
        "recommendations": builder.recommend_top_icps(clusters),
        "report": builder.generate_report(clusters, brand_name),
        "stats": {
            "total_clusters": len(clusters),
            "total_snippets": sum(c.snippet_count for c in clusters),
            "top_triggers": list(set(c.trigger_label for c in clusters[:5])),
            "top_blockers": list(set(c.blocker_label for c in clusters[:5]))
        }
    }
