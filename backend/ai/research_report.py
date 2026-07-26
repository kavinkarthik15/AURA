from __future__ import annotations

from typing import Any, Dict, List


class ResearchReportGenerator:
    def generate_report(
        self,
        title: str,
        architecture: Dict[str, Any],
        benchmarks: Dict[str, Any],
        ablation: Dict[str, Any],
        performance: Dict[str, Any],
        improvements: List[str],
        future_work: List[str],
    ) -> str:
        sections = [
            title,
            "",
            "Architecture",
            "-" * 12,
            "\n".join(f"- {name}: {value}" for name, value in architecture.items()),
            "",
            "Benchmarks",
            "-" * 10,
            "\n".join(f"- {name}: {value}" for name, value in benchmarks.items()),
            "",
            "Ablation",
            "-" * 8,
            "\n".join(f"- {name}: {value}" for name, value in ablation.items()),
            "",
            "Performance",
            "-" * 11,
            "\n".join(f"- {name}: {value}" for name, value in performance.items()),
            "",
            "Improvements",
            "-" * 12,
            "\n".join(f"- {item}" for item in improvements),
            "",
            "Future Work",
            "-" * 11,
            "\n".join(f"- {item}" for item in future_work),
        ]
        return "\n".join(sections)
