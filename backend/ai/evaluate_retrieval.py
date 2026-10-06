from __future__ import annotations

from typing import Any, Dict, Iterable, List

class RetrievalEvaluator:
    def evaluate(self, memory_gateway: Any, queries: Iterable[Dict[str, Any]], top_k: int = 3) -> Dict[str, Any]:
        query_list = list(queries)
        if not query_list:
            return {"queries": 0, "retrieval_precision": 0.0, "retrieval_recall": 0.0, "average_similarity": 0.0, "planning_improvement": 0.0, "retrieval_time_ms": 0.0}
        relevant_retrieved = 0
        relevant_total = 0
        similarities: List[float] = []
        retrieval_time = 0.0
        for query in query_list:
            if hasattr(memory_gateway, "retrieve_experiences"):
                result = memory_gateway.retrieve_experiences(
                    query.get("state", {}), query.get("goal", ""), query.get("actions", []), top_k=top_k
                )
            else:
                result = memory_gateway.retrieve(
                    query.get("state", {}), query.get("goal", ""), query.get("actions", []), top_k=top_k
                )
            matches = result["matches"]
            retrieval_time += result["retrieval_time_ms"]
            relevant = set(query.get("relevant_experience_ids", []))
            relevant_total += len(relevant)
            relevant_retrieved += len(relevant & {item.experience_id for item in matches})
            similarities.extend(item.similarity for item in matches)
        precision = relevant_retrieved / max(1, sum(min(top_k, len(query.get("relevant_experience_ids", []))) for query in query_list))
        recall = relevant_retrieved / max(1, relevant_total)
        return {"queries": len(query_list), "retrieval_precision": round(precision, 4), "retrieval_recall": round(recall, 4), "average_similarity": round(sum(similarities) / max(1, len(similarities)), 4), "planning_improvement": round(recall * 100, 4), "retrieval_time_ms": round(retrieval_time / len(query_list), 4)}
