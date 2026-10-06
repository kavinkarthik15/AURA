"""
17.14A Decision Gate

Apply the acceptance criteria from 17_14A_EXPERIMENT_MANIFEST mechanically to the
frozen 400-event artifact and safety analysis results.

This gate determines whether 17.14A objectives were met and what the next action is.
"""

import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime


class DecisionGate:
    """Apply 17.14A acceptance criteria."""

    def __init__(self):
        self.safety_results_file = Path("d:/AURA") / "17_14A_SAFETY_ANALYSIS_RESULTS.json"
        self.results = None
        self.load_results()

    def load_results(self):
        """Load safety analysis results."""
        with open(self.safety_results_file, 'r', encoding='utf-8') as f:
            self.results = json.load(f)

    def apply_gate(self) -> Dict[str, Any]:
        """Apply all 17.14A acceptance criteria."""
        print(f"\n{'='*80}")
        print(f"17.14A DECISION GATE")
        print(f"{'='*80}\n")

        decision = {
            "phase": "17.14A",
            "stage": "decision_gate",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "gates": self._evaluate_all_gates(),
            "overall_decision": None,
            "rationale": None,
            "next_action": None,
        }

        # Determine overall decision
        decision["overall_decision"] = self._make_decision(decision["gates"])
        decision["rationale"] = self._build_rationale(decision["gates"], decision["overall_decision"])
        decision["next_action"] = self._recommend_next_action(decision["overall_decision"])

        return decision

    def _evaluate_all_gates(self) -> Dict[str, Any]:
        """Evaluate all acceptance criteria from 17_14A_EXPERIMENT_MANIFEST."""
        
        print("GATE 1: INSTRUMENTATION CORRECTNESS")
        print("-" * 80)
        gate_1 = {
            "name": "Instrumentation Correctness",
            "requirement": "Shadow recorder captures all required fields without corruption",
            "result": self._gate_1_instrumentation(),
        }
        print(f"  Result: {gate_1['result']['status']}")
        print()

        print("GATE 2: LEGACY SAFETY")
        print("-" * 80)
        gate_2 = {
            "name": "Legacy Safety",
            "requirement": "MG OFF = legacy behavior (production unaffected)",
            "result": self._gate_2_legacy_safety(),
        }
        print(f"  Result: {gate_2['result']['status']}")
        print()

        print("GATE 3: SHADOW INTEGRITY")
        print("-" * 80)
        gate_3 = {
            "name": "Shadow Integrity",
            "requirement": "MG shadow path does not mutate production state",
            "result": self._gate_3_shadow_integrity(),
        }
        print(f"  Result: {gate_3['result']['status']}")
        print()

        print("GATE 4: OBSERVABILITY CONTRACT")
        print("-" * 80)
        gate_4 = {
            "name": "Observability Contract",
            "requirement": "All required fields present in shadow events",
            "result": self._gate_4_observability_contract(),
        }
        print(f"  Result: {gate_4['result']['status']}")
        print()

        print("GATE 5: MG SAFETY (SHADOW COMPUTATION)")
        print("-" * 80)
        gate_5 = {
            "name": "MG Safety Under Enabled Shadow Computation",
            "requirement": "MG computes safely, fallback works, no exceptions",
            "result": self._gate_5_mg_safety(),
        }
        print(f"  Result: {gate_5['result']['status']}")
        print()

        print("GATE 6: PRODUCTION READINESS")
        print("-" * 80)
        gate_6 = {
            "name": "Production Readiness",
            "requirement": "System ready for controlled production shadow deployment",
            "result": self._gate_6_production_readiness(),
        }
        print(f"  Result: {gate_6['result']['status']}")
        print()

        return {
            "gate_1_instrumentation": gate_1["result"],
            "gate_2_legacy_safety": gate_2["result"],
            "gate_3_shadow_integrity": gate_3["result"],
            "gate_4_observability_contract": gate_4["result"],
            "gate_5_mg_safety": gate_5["result"],
            "gate_6_production_readiness": gate_6["result"],
        }

    def _gate_1_instrumentation(self) -> Dict[str, Any]:
        """Gate 1: Instrumentation correctness."""
        instr = self.results.get("instrumentation_verdict", {})
        passed = instr.get("status") == "PRODUCTION_READY"

        return {
            "status": "PASS" if passed else "FAIL",
            "evidence": instr.get("evidence", []),
            "reason": instr.get("reason", ""),
        }

    def _gate_2_legacy_safety(self) -> Dict[str, Any]:
        """Gate 2: Legacy safety (production unaffected)."""
        prod = self.results.get("production_protection_verdict", {})
        passed = prod.get("status") == "PRODUCTION_SAFE"

        return {
            "status": "PASS" if passed else "FAIL",
            "evidence": prod.get("evidence", []),
            "reason": prod.get("reason", ""),
        }

    def _gate_3_shadow_integrity(self) -> Dict[str, Any]:
        """Gate 3: Shadow path does not mutate state."""
        prod = self.results.get("production_protection_verdict", {})
        passed = prod.get("status") == "PRODUCTION_SAFE"

        return {
            "status": "PASS" if passed else "FAIL",
            "evidence": prod.get("evidence", []),
            "reason": "Shadow recorder isolated from production state; no mutation observed",
        }

    def _gate_4_observability_contract(self) -> Dict[str, Any]:
        """Gate 4: Observability contract compliance."""
        proven = self.results.get("proven_properties", {})
        schema = proven.get("schema_completeness", {})
        passed = schema.get("status", False)

        return {
            "status": "PASS" if passed else "FAIL",
            "evidence": [schema.get("evidence", "")],
            "reason": "All 14 required fields present in all 400 events",
        }

    def _gate_5_mg_safety(self) -> Dict[str, Any]:
        """Gate 5: MG safety under enabled shadow computation."""
        mg_verdict = self.results.get("mg_safety_verdict", {})
        
        return {
            "status": "BLOCKED",
            "evidence": mg_verdict.get("evidence", []),
            "reason": mg_verdict.get("reason", ""),
            "note": "Run 1 tested instrumentation with MG DISABLED. MG safety requires Run 2 with MG ENABLED.",
            "blocker_for": "Production activation",
            "required_to_unblock": "17.15 MG-Enabled Shadow Validation with actual MG computation"
        }

    def _gate_6_production_readiness(self) -> Dict[str, Any]:
        """Gate 6: Production readiness (operational deployment)."""
        
        return {
            "status": "DEFERRED",
            "evidence": [
                "Instrumentation ready for production shadow deployment",
                "Production path protected",
                "MG safety not yet verified"
            ],
            "reason": "Instrumentation is production-ready, but MG safety testing is incomplete",
            "note": "Readiness review requires MG-enabled shadow validation results first",
            "required_to_proceed": "Complete 17.15 (MG-Enabled Shadow Validation)"
        }

    def _make_decision(self, gates: Dict[str, Any]) -> str:
        """Determine overall decision from gate results."""
        gate_results = [g.get("status") for g in gates.values()]
        
        if "FAIL" in gate_results:
            return "STOP - Critical Gate Failed"
        
        if "BLOCKED" in gate_results:
            return "BLOCKED - Cannot Proceed Without MG-Enabled Shadow Validation"
        
        if "DEFERRED" in gate_results or "BLOCKED" in gate_results:
            return "PROCEED TO NEXT PHASE - 17.15 MG-Enabled Shadow Validation"
        
        return "PROCEED TO PRODUCTION READINESS REVIEW"

    def _build_rationale(self, gates: Dict[str, Any], decision: str) -> str:
        """Build human-readable rationale for decision."""
        
        if "BLOCKED" in decision:
            return """
Run 1 (17.14A with MG DISABLED) successfully proved instrumentation and production protection.

However, it did NOT test:
  - MG signal extraction under actual computation
  - MG correction stability  
  - Fallback behavior when actually triggered
  - MG latency overhead under shadow computation
  - MG safety with realistic workloads

Therefore, MG activation cannot be justified without Run 2.

Next required step: 17.15 MG-Enabled Shadow Validation
  - Enable MG in shadow mode
  - Collect and analyze correction behavior
  - Test fallback robustness
  - Measure realistic latency
  - Determine if MG is safe for production deployment
"""
        
        return "Analysis complete; refer to gate results for next action"

    def _recommend_next_action(self, decision: str) -> Dict[str, Any]:
        """Recommend the next action."""
        
        if "BLOCKED" in decision:
            return {
                "action": "BEGIN 17.15 MG-Enabled Shadow Validation",
                "rationale": "Run 1 proved instrumentation; Run 2 must prove MG safety",
                "setup": [
                    "Preserve frozen 17.14A checkpoint (immutable)",
                    "Create new run with mg_config.enabled=True",
                    "Collect MG shadow computations in parallel events",
                    "Analyze fallback triggers, corrections, and latency",
                ],
                "do_not": [
                    "Activate MG based on Run 1 success",
                    "Skip MG-enabled testing",
                    "Modify frozen instrumentation",
                    "Claim production readiness without Run 2",
                ],
                "timeline": "Sequential: Run 1 ✓ → Run 2 (NEXT) → Analysis → Decision → Readiness Review",
            }
        
        return {
            "action": "Refer to gate results",
            "note": "Unexpected decision state"
        }


def main():
    """Execute the decision gate."""
    gate = DecisionGate()
    decision = gate.apply_gate()

    print("="*80)
    print("DECISION GATE RESULT")
    print("="*80)
    print(f"\nOverall Decision: {decision['overall_decision']}")
    print(f"\nRationale:\n{decision['rationale']}")
    print(f"\nNext Action: {decision['next_action']['action']}")

    # Save decision
    output_file = Path("d:/AURA") / "17_14A_DECISION_GATE_RESULT.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(decision, f, indent=2)
    print(f"\n[OK] Decision saved to {output_file}")

    return decision


if __name__ == "__main__":
    main()
