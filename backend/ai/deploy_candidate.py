from typing import Any, Dict


class DeployCandidate:
    def __init__(self, min_r2_gain: float = 0.0, mae_tolerance: float = 1.05) -> None:
        self.min_r2_gain = min_r2_gain
        self.mae_tolerance = mae_tolerance

    def deploy(self, candidate: Dict[str, Any], benchmark: Dict[str, Any]) -> Dict[str, Any]:
        deployed_metrics = benchmark.get("baseline_metrics") or {}
        candidate_metrics = benchmark.get("candidate_metrics") or {}

        if not candidate_metrics:
            return {
                "deployed": False,
                "reason": "candidate metrics were not provided",
                "candidate_version": candidate.get("model_version"),
            }

        candidate_r2 = float(candidate_metrics.get("r2", 0.0))
        deployed_r2 = float(deployed_metrics.get("r2", 0.0))
        candidate_mae = float(candidate_metrics.get("mae", 0.0))
        deployed_mae = float(deployed_metrics.get("mae", 0.0))

        r2_improved = candidate_r2 > deployed_r2 + self.min_r2_gain
        mae_within_tolerance = candidate_mae <= deployed_mae * self.mae_tolerance if deployed_mae else True

        if r2_improved and mae_within_tolerance:
            return {
                "deployed": True,
                "reason": "candidate improved R² and stayed within the MAE tolerance",
                "candidate_version": candidate.get("model_version"),
                "model_path": candidate.get("model_path"),
            }

        reasons = []
        if not r2_improved:
            reasons.append("R² did not improve enough")
        if not mae_within_tolerance:
            reasons.append("MAE exceeded the allowed tolerance")
        return {
            "deployed": False,
            "reason": "; ".join(reasons) if reasons else "candidate did not satisfy the deployment criteria",
            "candidate_version": candidate.get("model_version"),
        }
