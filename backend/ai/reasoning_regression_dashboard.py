from __future__ import annotations

from typing import Any, Dict, List


class ReasoningRegressionDashboard:
    def __init__(self) -> None:
        self.version = "reasoning_regression_dashboard_v1"

    def summarize(
        self,
        history: List[Dict[str, Any]],
        accuracy: float,
        confidence_calibration: float,
        contradiction_rate: float,
        benchmark_trend: float,
    ) -> Dict[str, Any]:
        average_accuracy = (
            round(sum(item.get("accuracy", 0.0) for item in history) / max(1, len(history)), 2)
            if history
            else round(accuracy, 2)
        )
        average_confidence = (
            round(sum(item.get("confidence", 0.0) for item in history) / max(1, len(history)), 2)
            if history
            else round(confidence_calibration, 2)
        )
        return {
            "accuracy": round(accuracy, 2),
            "confidence_calibration": round(confidence_calibration, 2),
            "contradiction_rate": round(contradiction_rate, 2),
            "benchmark_trend": round(benchmark_trend, 2),
            "history_average_accuracy": average_accuracy,
            "history_average_confidence": average_confidence,
            "trend": "improving" if benchmark_trend > 0 else "stable",
        }
