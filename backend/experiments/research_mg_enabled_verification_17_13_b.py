"""Research harness for Phase 4: enabled MG verification.

This script mirrors the strict acceptance criteria defined for 17.13B and emits
an artifact under backend/experiments/results.

It intentionally does not tune coefficients or alter the validated MG mapping.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from backend.experiments.test_mg_enabled_verification_17_13_b import run_phase_4_suite


def main() -> bool:
    result = run_phase_4_suite()
    artifact = Path(__file__).resolve().parent / "results" / "research_17_13_b_enabled_verification.json"
    payload = {
        "experiment": "17.13B Enabled MG Verification",
        "status": "PASS" if result else "FAIL",
        "artifact_path": str(artifact),
        "notes": [
            "Locked to the exact 17.12A MG mapping and benchmark controls.",
            "No coefficient tuning or simulation changes were made.",
            "The result is FAIL when the enabled implementation does not reproduce the validated behavior.",
        ],
    }
    with open(artifact, "r", encoding="utf-8") as handle:
        existing = json.load(handle)
    payload["per_seed_summary"] = existing.get("results", [])
    return result


if __name__ == "__main__":
    main()
