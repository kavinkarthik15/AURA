from typing import Any, Dict


class BenchmarkCandidate:
    def benchmark(self, candidate: Dict[str, Any], baseline: Dict[str, Any] | None = None) -> Dict[str, Any]:
        baseline_score = float(baseline.get("mae", 0.0)) if baseline else 0.0
        candidate_score = float(candidate.get("mae", 0.0))
        improvement = baseline_score - candidate_score if baseline_score else 0.0
        baseline_metrics = {
            "mae": float(baseline.get("mae", 0.0)) if baseline else 0.0,
            "mse": float(baseline.get("mse", 0.0)) if baseline else 0.0,
            "r2": float(baseline.get("r2", 0.0)) if baseline else 0.0,
        }
        candidate_metrics = {
            "mae": candidate_score,
            "mse": candidate_score,
            "r2": max(0.0, 1.0 - max(candidate_score, 0.0)),
        }
        return {
            "candidate_version": candidate.get("model_version"),
            "baseline_version": baseline.get("model_version") if baseline else None,
            "candidate_score": candidate_score,
            "baseline_score": baseline_score,
            "improvement": improvement,
            "accepted": candidate_score <= baseline_score if baseline else True,
            "baseline_metrics": baseline_metrics,
            "candidate_metrics": candidate_metrics,
        }
