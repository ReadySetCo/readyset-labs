"""
Proto-ICP Clusterer - Groups snippets by Trigger × Blocker to form ICP candidates.
Per Intake Engine brief, creates cluster table with counts, phrases, and representative snippets.
"""

from typing import Dict, Any, List
from collections import defaultdict


class ProtoICPClusterer:
    """
    Clusters snippets by Primary Trigger × Blocker Type to identify ICP candidates.
    Output format matches brief: cluster_id, trigger, blocker, snippet_count, top phrases, examples.
    """
    
    def cluster_snippets(
        self, 
        snippets: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Cluster snippets by Trigger × Blocker combination.
        
        Args:
            snippets: List of classified snippets with primary_trigger, blocker_type, etc.
            
        Returns:
            Dict with clusters and metadata
        """
        # Group by Trigger × Blocker
        clusters = defaultdict(lambda: {
            "snippets": [],
            "language_cues": [],
            "desired_outcomes": defaultdict(int),
            "proof_types": defaultdict(int),
            "sources": defaultdict(int)
        })
        
        for snippet in snippets:
            trigger = snippet.get("primary_trigger") or "unknown"
            blocker = snippet.get("blocker_type") or "none"
            cluster_key = f"{trigger}___{blocker}"
            
            clusters[cluster_key]["snippets"].append(snippet)
            
            # Collect language cues
            cues = snippet.get("language_cues") or []
            if isinstance(cues, list):
                clusters[cluster_key]["language_cues"].extend(cues)
            
            # Count desired outcomes
            outcome = snippet.get("desired_outcome_level") or "unknown"
            clusters[cluster_key]["desired_outcomes"][outcome] += 1
            
            # Count proof types
            proof = snippet.get("proof_type_trusted") or "none"
            clusters[cluster_key]["proof_types"][proof] += 1
            
            # Count sources
            source = snippet.get("source_type") or "unknown"
            clusters[cluster_key]["sources"][source] += 1
        
        # Build cluster table
        cluster_table = []
        for i, (cluster_key, data) in enumerate(sorted(
            clusters.items(), 
            key=lambda x: len(x[1]["snippets"]), 
            reverse=True
        )):
            trigger, blocker = cluster_key.split("___")
            
            # Get top language cues (most common)
            cue_counts = defaultdict(int)
            for cue in data["language_cues"]:
                if cue:
                    cue_counts[cue.lower()] += 1
            top_cues = [cue for cue, _ in sorted(cue_counts.items(), key=lambda x: x[1], reverse=True)[:5]]
            
            # Get representative snippets (3-5)
            representative = []
            for snippet in data["snippets"][:5]:
                representative.append({
                    "content": snippet.get("content", "")[:300],
                    "source_type": snippet.get("source_type"),
                    "source_url": snippet.get("source_url"),
                    "confidence": snippet.get("classification_confidence", snippet.get("confidence", 0.5))
                })
            
            cluster_table.append({
                "cluster_id": f"C{i+1:02d}",
                "trigger_label": trigger,
                "blocker_label": blocker,
                "snippet_count": len(data["snippets"]),
                "top_language_cues": top_cues,
                "desired_outcomes_distribution": dict(data["desired_outcomes"]),
                "proof_types_distribution": dict(data["proof_types"]),
                "sources_distribution": dict(data["sources"]),
                "representative_snippets": representative
            })
        
        return {
            "total_snippets": len(snippets),
            "total_clusters": len(cluster_table),
            "clusters": cluster_table
        }
    
    def recommend_top_icps(
        self, 
        cluster_result: Dict[str, Any],
        top_n: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Recommend top ICP candidates based on cluster analysis.
        
        Scoring logic per brief:
        - Frequency (cluster size)
        - Distinctiveness (unique blocker or proof type)
        - Evidence quality (snippet clarity/confidence)
        
        Args:
            cluster_result: Output from cluster_snippets()
            top_n: Number of recommendations
            
        Returns:
            List of recommended ICP candidates with rationale
        """
        clusters = cluster_result.get("clusters", [])
        if not clusters:
            return []
        
        # Score each cluster
        scored = []
        all_blockers = set(c["blocker_label"] for c in clusters)
        all_triggers = set(c["trigger_label"] for c in clusters)
        
        for cluster in clusters:
            # Frequency score (normalized)
            max_count = max(c["snippet_count"] for c in clusters)
            frequency_score = cluster["snippet_count"] / max_count if max_count > 0 else 0
            
            # Distinctiveness score
            # Higher if this is the only cluster with this blocker/trigger combo
            blocker_count = sum(1 for c in clusters if c["blocker_label"] == cluster["blocker_label"])
            trigger_count = sum(1 for c in clusters if c["trigger_label"] == cluster["trigger_label"])
            distinctiveness_score = 1.0 - (min(blocker_count, trigger_count) / len(clusters))
            
            # Evidence quality (average confidence of representative snippets)
            confidences = [s.get("confidence", 0.5) for s in cluster["representative_snippets"]]
            evidence_score = sum(confidences) / len(confidences) if confidences else 0.5
            
            # Combined score
            total_score = (frequency_score * 0.4) + (distinctiveness_score * 0.3) + (evidence_score * 0.3)
            
            # Identify risks/missing evidence
            risks = []
            if cluster["snippet_count"] < 5:
                risks.append("Low sample size")
            if not cluster["top_language_cues"]:
                risks.append("No clear language patterns")
            if len(cluster["proof_types_distribution"]) == 0 or list(cluster["proof_types_distribution"].keys()) == ["none"]:
                risks.append("No proof type identified")
            
            scored.append({
                **cluster,
                "score": round(total_score, 3),
                "frequency_score": round(frequency_score, 2),
                "distinctiveness_score": round(distinctiveness_score, 2),
                "evidence_score": round(evidence_score, 2),
                "rationale": self._generate_rationale(cluster),
                "risks": risks if risks else ["None identified"]
            })
        
        # Sort by score and return top N
        scored.sort(key=lambda x: x["score"], reverse=True)
        
        recommendations = []
        for i, cluster in enumerate(scored[:top_n]):
            recommendations.append({
                "rank": i + 1,
                "cluster_id": cluster["cluster_id"],
                "trigger": cluster["trigger_label"],
                "blocker": cluster["blocker_label"],
                "snippet_count": cluster["snippet_count"],
                "score": cluster["score"],
                "rationale": cluster["rationale"],
                "risks": cluster["risks"],
                "top_phrases": cluster["top_language_cues"],
                "dominant_outcome": max(
                    cluster["desired_outcomes_distribution"].items(), 
                    key=lambda x: x[1],
                    default=("unknown", 0)
                )[0],
                "dominant_proof": max(
                    cluster["proof_types_distribution"].items(),
                    key=lambda x: x[1],
                    default=("unknown", 0)
                )[0]
            })
        
        return recommendations
    
    def _generate_rationale(self, cluster: Dict[str, Any]) -> str:
        """Generate a brief rationale for the cluster's ICP potential."""
        trigger = cluster["trigger_label"]
        blocker = cluster["blocker_label"]
        count = cluster["snippet_count"]
        
        outcome = max(
            cluster["desired_outcomes_distribution"].items(),
            key=lambda x: x[1],
            default=("functional", 0)
        )[0]
        
        proof = max(
            cluster["proof_types_distribution"].items(),
            key=lambda x: x[1],
            default=("none", 0)
        )[0]
        
        rationale = f"Customers triggered by '{trigger}'"
        
        if blocker != "none":
            if blocker == "friction":
                rationale += f" face barriers (can't)"
            else:
                rationale += f" have objections (won't)"
        
        rationale += f". Primary need is {outcome}. "
        
        if proof != "none":
            rationale += f"Trust {proof.replace('_', ' ')} as evidence. "
        
        rationale += f"({count} snippets support this.)"
        
        return rationale


def generate_proto_icp_report(snippets: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate complete Proto-ICP report from classified snippets.
    
    Args:
        snippets: List of classified snippets
        
    Returns:
        Complete report with clusters and recommendations
    """
    clusterer = ProtoICPClusterer()
    
    # Filter to only classified snippets
    classified = [s for s in snippets if s.get("primary_trigger")]
    
    if not classified:
        return {
            "status": "no_classified_snippets",
            "message": "No classified snippets available. Run classification first.",
            "total_snippets": len(snippets),
            "classified_snippets": 0
        }
    
    # Cluster
    cluster_result = clusterer.cluster_snippets(classified)
    
    # Get recommendations
    recommendations = clusterer.recommend_top_icps(cluster_result, top_n=3)
    
    return {
        "status": "success",
        "total_snippets": len(snippets),
        "classified_snippets": len(classified),
        "classification_coverage": round(len(classified) / len(snippets) * 100, 1) if snippets else 0,
        "cluster_summary": {
            "total_clusters": cluster_result["total_clusters"],
            "clusters": cluster_result["clusters"]
        },
        "recommended_icps": recommendations
    }
