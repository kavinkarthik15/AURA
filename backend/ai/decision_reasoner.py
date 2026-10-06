from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import uuid4

from backend.ai.context_builder import PlanningContext
from backend.ai.reasoning_confidence import ReasoningConfidenceModel


@dataclass
class Prediction:
    reward: float = 0.0
    risk: float = 0.0
    cost: float = 0.0
    duration: float = 0.0
    utility: float = 0.0
    confidence: float = 0.0
    expected_state_change: Dict[str, float] = field(default_factory=dict)
    predicted_state: Dict[str, float] = field(default_factory=dict)


@dataclass
class Evidence:
    supporting_experiences: List[str] = field(default_factory=list)
    supporting_knowledge: List[str] = field(default_factory=list)
    supporting_reflections: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    alternative_actions: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    blocking_constraints: List[str] = field(default_factory=list)
    reasoning: str = ""


@dataclass
class DecisionCandidate:
    decision_id: str
    action: Any
    goal_supported: str
    expected_outcome: str
    prediction: Prediction = field(default_factory=Prediction)
    evidence: Evidence = field(default_factory=Evidence)
    goal_alignment: Dict[str, float] = field(default_factory=dict)
    estimated_duration: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "action": self.action,
            "goal_supported": self.goal_supported,
            "goal_alignment": self.goal_alignment,
            "expected_outcome": self.expected_outcome,
            "prediction": {
                "reward": self.prediction.reward,
                "risk": self.prediction.risk,
                "cost": self.prediction.cost,
                "duration": self.prediction.duration,
                "utility": self.prediction.utility,
                "expected_state_change": self.prediction.expected_state_change,
                "predicted_state": self.prediction.predicted_state,
            },
            "evidence": {
                "supporting_experiences": self.evidence.supporting_experiences,
                "supporting_knowledge": self.evidence.supporting_knowledge,
                "supporting_reflections": self.evidence.supporting_reflections,
                "risks": self.evidence.risks,
                "alternative_actions": self.evidence.alternative_actions,
                "assumptions": self.evidence.assumptions,
                "blocking_constraints": self.evidence.blocking_constraints,
                "reasoning": self.evidence.reasoning,
            },
            "estimated_duration": self.estimated_duration,
            "created_at": self.created_at,
        }

    # Backwards-compatible properties for existing callers/tests
    @property
    def expected_reward(self) -> float:
        return self.prediction.reward

    @property
    def expected_risk(self) -> float:
        return self.prediction.risk

    @property
    def expected_cost(self) -> float:
        return self.prediction.cost

    @property
    def confidence(self) -> float:
        return getattr(self.prediction, "confidence", 0.0)

    @property
    def utility_score(self) -> float:
        return self.prediction.utility

    @property
    def expected_state_change(self) -> Dict[str, float]:
        return self.prediction.expected_state_change

    @property
    def predicted_state(self) -> Dict[str, float]:
        return self.prediction.predicted_state

    @property
    def reasoning(self) -> str:
        return self.evidence.reasoning

    @property
    def supporting_knowledge(self) -> List[str]:
        return self.evidence.supporting_knowledge

    @property
    def supporting_experiences(self) -> List[str]:
        return self.evidence.supporting_experiences

    @property
    def supporting_reflections(self) -> List[str]:
        return self.evidence.supporting_reflections

    @property
    def assumptions(self) -> List[str]:
        return self.evidence.assumptions

    @property
    def alternative_actions(self) -> List[str]:
        return self.evidence.alternative_actions

    @property
    def blocking_constraints(self) -> List[str]:
        return self.evidence.blocking_constraints


class DecisionReasoner:
    def __init__(self, memory_manager: object | None = None) -> None:
        self.memory_manager = memory_manager
        self.version = "decision_reasoner_v1"

    def generate_candidates(self, context: PlanningContext) -> List[DecisionCandidate]:
        candidates: List[DecisionCandidate] = []
        if context.candidate_plans:
            for plan in context.candidate_plans:
                action_label = plan if isinstance(plan, str) else str(plan)
                candidates.append(self._build_candidate_from_plan(action_label, context))
        else:
            candidates.extend(self._build_candidates_from_knowledge(context))
        return sorted(candidates, key=lambda candidate: candidate.utility_score, reverse=True)

    def _build_candidate_from_plan(self, plan: Any, context: PlanningContext) -> DecisionCandidate:
        decision_id = f"DEC-{uuid4().hex[:12].upper()}"
        supporting_experiences = [
            str(item.get("memory_id", item.get("experience_id", "")))
            for item in context.relevant_experiences
            if isinstance(item, dict) and (item.get("memory_id") or item.get("experience_id"))
        ]
        supporting_knowledge = [
            str(
                item.get("knowledge_id")
                if item.get("knowledge_id")
                else item.get("knowledge", {}).get("knowledge_id", "")
            )
            for item in context.relevant_knowledge
            if isinstance(item, dict) and (item.get("knowledge_id") or (item.get("knowledge") and item.get("knowledge").get("knowledge_id")))
        ]
        supporting_reflections = [str(item.get("goal", "")) for item in context.relevant_reflections if isinstance(item, dict) and item.get("goal")]
        risks = [statement for statement in self._knowledge_statements(context) if any(term in statement.lower() for term in ["risk", "fatigue", "failure", "avoid"])]
        assumptions = [f"Supports goal {context.goal}"] if context.goal else []
        blocking_constraints = [str(item.get("value")) for item in context.candidate_plans if isinstance(item, dict) and item.get("type") == "constraint"]
        expected_outcome = self._predict_outcome(plan, context)
        confidence = self._estimate_confidence(context, len(supporting_experiences), len(supporting_knowledge), len(supporting_reflections))
        expected_reward = self._estimate_reward(context, plan)
        expected_cost = self._estimate_cost(context, plan)
        expected_risk = self._estimate_risk(context, plan)
        expected_state_change = self._estimate_state_change(plan, context)
        goal_alignment = self._estimate_goal_alignment(context, confidence)
        reasoning = self._summarize_reasoning(plan, context)
        alternative_actions = [str(plan)] if isinstance(plan, str) else [str(plan)]
        utility_score = self._compute_utility(expected_reward, expected_risk, expected_cost, confidence)
        estimated_duration = self._estimate_duration(plan)
        # build prediction and evidence objects
        predicted_state = dict(context.current_state or {})
        for k, v in expected_state_change.items():
            try:
                predicted_state[k] = predicted_state.get(k, 0) + v
            except Exception:
                predicted_state[k] = v

        prediction = Prediction(
            reward=expected_reward,
            risk=expected_risk,
            cost=expected_cost,
            duration=estimated_duration,
            utility=utility_score,
            confidence=confidence,
            expected_state_change=expected_state_change,
            predicted_state={k: round(float(v), 4) for k, v in predicted_state.items()},
        )

        evidence = Evidence(
            supporting_experiences=supporting_experiences,
            supporting_knowledge=supporting_knowledge,
            supporting_reflections=supporting_reflections,
            risks=risks,
            alternative_actions=alternative_actions,
            assumptions=assumptions,
            blocking_constraints=blocking_constraints,
            reasoning=reasoning,
        )

        return DecisionCandidate(
            decision_id=decision_id,
            action=plan,
            goal_supported=context.goal,
            expected_outcome=expected_outcome,
            prediction=prediction,
            evidence=evidence,
            goal_alignment=goal_alignment,
            estimated_duration=estimated_duration,
        )

    def _build_candidates_from_knowledge(self, context: PlanningContext) -> List[DecisionCandidate]:
        candidates: List[DecisionCandidate] = []
        for record in context.relevant_knowledge:
            knowledge = record.get("knowledge") if isinstance(record, dict) and record.get("knowledge") is not None else record
            statement = knowledge.get("statement", "") if isinstance(knowledge, dict) else getattr(record, "statement", "")
            decision_id = f"DEC-{uuid4().hex[:12].upper()}"
            confidence = self._estimate_confidence(context, len(context.relevant_experiences), 1, len(context.relevant_reflections))
            expected_reward = self._estimate_reward(context, statement)
            expected_cost = self._estimate_cost(context, statement)
            expected_risk = self._estimate_risk(context, statement)
            expected_state_change = self._estimate_state_change(statement, context)
            goal_alignment = self._estimate_goal_alignment(context, confidence)
            utility_score = self._compute_utility(expected_reward, expected_risk, expected_cost, confidence)

            # build predicted state from current state + estimated change
            predicted_state = dict(context.current_state or {})
            for k, v in expected_state_change.items():
                try:
                    predicted_state[k] = predicted_state.get(k, 0) + v
                except Exception:
                    predicted_state[k] = v

            prediction = Prediction(
                reward=expected_reward,
                risk=expected_risk,
                cost=expected_cost,
                duration=self._estimate_duration(statement),
                utility=utility_score,
                confidence=confidence,
                expected_state_change=expected_state_change,
                predicted_state={k: round(float(v), 4) for k, v in predicted_state.items()},
            )

            evidence = Evidence(
                supporting_experiences=[
                    str(getattr(item, "memory_id", item.get("memory_id", item.get("experience_id", ""))))
                    if hasattr(item, "memory_id") or isinstance(item, dict)
                    else str(item)
                    for item in context.relevant_experiences
                ],
                supporting_knowledge=[
                    knowledge.get("knowledge_id", "")
                    if isinstance(knowledge, dict)
                    else getattr(record, "knowledge_id", "")
                ],
                supporting_reflections=[str(item.get("goal", "")) for item in context.relevant_reflections if isinstance(item, dict) and item.get("goal")],
                risks=[statement] if any(term in statement.lower() for term in ["risk", "fatigue", "failure", "avoid"]) else [],
                alternative_actions=[statement],
                assumptions=[f"Based on semantic knowledge for {context.goal}"],
                blocking_constraints=[],
                reasoning=f"Derived from knowledge: {statement}",
            )

            candidates.append(
                DecisionCandidate(
                    decision_id=decision_id,
                    action=statement,
                    goal_supported=context.goal,
                    expected_outcome=f"Likely improves goal progress toward {context.goal}",
                    prediction=prediction,
                    evidence=evidence,
                    goal_alignment=goal_alignment,
                    estimated_duration=self._estimate_duration(statement),
                )
            )
        return candidates

    def _predict_outcome(self, plan: Any, context: PlanningContext) -> str:
        if isinstance(plan, str) and "practice" in plan.lower():
            return "Increase skill progress and consistency"
        if isinstance(plan, str) and "study" in plan.lower():
            return "Improve retention and knowledge depth"
        return f"Move toward {context.goal} with moderate confidence"

    def _estimate_reward(self, context: PlanningContext, plan: Any) -> float:
        if isinstance(plan, dict) and plan.get("expected_reward") is not None:
            return float(plan["expected_reward"])
        if isinstance(plan, str):
            reward = 0.4 + 0.04 * len(plan.split())
            return round(min(reward, 0.95), 4)
        return 0.5

    def _estimate_cost(self, context: PlanningContext, plan: Any) -> float:
        if isinstance(plan, dict) and plan.get("expected_cost") is not None:
            return float(plan["expected_cost"])
        if isinstance(plan, str):
            cost = 0.15 + 0.03 * len(plan.split())
            return round(min(cost, 0.9), 4)
        return 0.25

    def _estimate_risk(self, context: PlanningContext, plan: Any) -> float:
        if isinstance(plan, dict) and plan.get("expected_risk") is not None:
            return float(plan["expected_risk"])
        if isinstance(plan, str):
            risk_terms = ["risk", "fail", "delay", "overwhelm", "fatigue"]
            risk = 0.2 + 0.08 * sum(1 for term in risk_terms if term in plan.lower())
            return round(min(risk, 0.9), 4)
        return 0.2

    def _compute_utility(self, reward: float, risk: float, cost: float, confidence: float) -> float:
        utility = reward * confidence - (risk * 0.6 + cost * 0.4)
        return round(max(0.0, min(utility, 1.0)), 4)

    def _estimate_duration(self, plan: Any) -> float:
        if isinstance(plan, dict) and plan.get("estimated_duration") is not None:
            return float(plan["estimated_duration"])
        if isinstance(plan, str):
            duration = 0.5 * len(plan.split())
            return round(min(duration, 8.0), 2)
        return 1.0

    def _estimate_state_change(self, plan: Any, context: PlanningContext) -> Dict[str, float]:
        if isinstance(plan, dict) and plan.get("expected_state_change") is not None:
            return {k: float(v) for k, v in plan["expected_state_change"].items()}
        if isinstance(plan, str):
            changes: Dict[str, float] = {}
            lower = plan.lower()
            if "practice" in lower:
                changes["python_skill"] = 3.0
                changes["confidence"] = 0.4
            if "study" in lower:
                changes["knowledge_depth"] = 3.0
                changes["confidence"] = changes.get("confidence", 0.0) + 0.3
            if "project" in lower or "complete" in lower:
                changes["project_completion"] = 5.0
                changes["confidence"] = changes.get("confidence", 0.0) + 0.2
            if not changes:
                changes["confidence"] = 0.1
            return {k: round(v, 4) for k, v in changes.items()}
        return {}

    def _estimate_goal_alignment(self, context: PlanningContext, confidence: float) -> Dict[str, float]:
        if not context.goal:
            return {}
        return {context.goal: round(min(1.0, confidence + 0.05), 4)}

    def _estimate_confidence(self, context: PlanningContext, experiences: int, knowledge: int, reflections: int) -> float:
        base = 0.3 + 0.1 * min(experiences, 3) + 0.1 * min(knowledge, 3) + 0.05 * min(reflections, 2)
        return round(min(0.99, base + 0.05 * len(context.candidate_plans)), 4)

    def _summarize_reasoning(self, plan: Any, context: PlanningContext) -> str:
        plan_text = str(plan)
        rules = ", ".join([statement for statement in self._knowledge_statements(context)][:2])
        return f"Recommend {plan_text} because {rules or 'it matches the current planning context and available knowledge.'}"

    def _knowledge_statements(self, context: PlanningContext) -> List[str]:
        statements: List[str] = []
        for record in context.relevant_knowledge:
            knowledge = record.get("knowledge") if isinstance(record, dict) and record.get("knowledge") is not None else record
            if isinstance(knowledge, dict) and knowledge.get("statement"):
                statements.append(str(knowledge["statement"]))
            elif not isinstance(knowledge, dict) and getattr(record, "statement", None):
                statements.append(str(getattr(record, "statement", "")))
        return statements
