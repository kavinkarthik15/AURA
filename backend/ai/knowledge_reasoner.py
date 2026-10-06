from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from backend.ai.context_builder import PlanningContext
from backend.ai.reasoning_confidence import ReasoningConfidenceModel


@dataclass
class KnowledgeInsight:
    applicable_rules: List[str] = field(default_factory=list)
    inferred_constraints: List[str] = field(default_factory=list)
    inferred_opportunities: List[str] = field(default_factory=list)
    inferred_risks: List[str] = field(default_factory=list)
    supporting_knowledge: List[str] = field(default_factory=list)
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "applicable_rules": self.applicable_rules,
            "inferred_constraints": self.inferred_constraints,
            "inferred_opportunities": self.inferred_opportunities,
            "inferred_risks": self.inferred_risks,
            "supporting_knowledge": self.supporting_knowledge,
            "confidence": self.confidence,
        }


class KnowledgeReasoner:
    def __init__(self, memory_manager: object | None = None) -> None:
        self.memory_manager = memory_manager
        self.version = "knowledge_reasoner_v1"

    def reason(self, context: PlanningContext) -> KnowledgeInsight:
        applicable_rules: List[str] = []
        inferred_constraints: List[str] = []
        inferred_opportunities: List[str] = []
        inferred_risks: List[str] = []
        supporting_knowledge: List[str] = []

        goal_lower = context.goal.lower()
        for record in context.relevant_knowledge:
            knowledge = record.get("knowledge") if isinstance(record, dict) and record.get("knowledge") is not None else record
            if isinstance(knowledge, dict):
                statement = str(knowledge.get("statement", "")).lower()
                concept = str(knowledge.get("concept", "")).lower()
                knowledge_id = knowledge.get("knowledge_id")
            else:
                statement = str(getattr(record, "statement", "")).lower()
                concept = str(getattr(record, "concept", "")).lower()
                knowledge_id = getattr(record, "knowledge_id", None)

            if goal_lower and goal_lower in statement:
                applicable_rules.append(knowledge.get("statement", "") if isinstance(knowledge, dict) else getattr(record, "statement", ""))
            if "avoid" in statement or "do not" in statement or "never" in statement:
                inferred_constraints.append(knowledge.get("statement", "") if isinstance(knowledge, dict) else getattr(record, "statement", ""))
            if "improve" in statement or "increase" in statement or "better" in statement:
                inferred_opportunities.append(knowledge.get("statement", "") if isinstance(knowledge, dict) else getattr(record, "statement", ""))
            if "risk" in statement or "fatigue" in statement or "failure" in statement:
                inferred_risks.append(knowledge.get("statement", "") if isinstance(knowledge, dict) else getattr(record, "statement", ""))
            if knowledge_id:
                supporting_knowledge.append(knowledge_id)
            elif isinstance(knowledge, dict) and knowledge.get("statement"):
                supporting_knowledge.append(knowledge.get("statement", ""))
            elif not isinstance(knowledge, dict) and getattr(record, "statement", None):
                supporting_knowledge.append(getattr(record, "statement", ""))

        if not applicable_rules and context.relevant_knowledge:
            first_record = context.relevant_knowledge[0]
            first_knowledge = None
            if isinstance(first_record, dict) and first_record.get("knowledge") is not None:
                first_knowledge = first_record["knowledge"].get("statement", "")
            elif isinstance(first_record, dict):
                first_knowledge = first_record.get("statement", "")
            else:
                first_knowledge = getattr(first_record, "statement", "")
            if first_knowledge:
                applicable_rules.append(first_knowledge)

        confidence = round(
            min(
                0.99,
                0.2
                + 0.15 * len(context.relevant_knowledge)
                + 0.1 * len(context.relevant_experiences)
                + 0.05 * len(context.relevant_reflections),
            ),
            4,
        )
        knowledge_count = len(context.relevant_knowledge)
        evidence_factor = len(supporting_knowledge) / max(1, knowledge_count)
        confidence_model = ReasoningConfidenceModel().score(
            len(context.relevant_experiences),
            len(inferred_risks),
            evidence_factor,
            confidence,
        )

        insight = KnowledgeInsight(
            applicable_rules=sorted(set(applicable_rules))[:5],
            inferred_constraints=sorted(set(inferred_constraints))[:5],
            inferred_opportunities=sorted(set(inferred_opportunities))[:5],
            inferred_risks=sorted(set(inferred_risks))[:5],
            supporting_knowledge=sorted(set(supporting_knowledge))[:10],
            confidence=round(confidence_model["reasoning_confidence"], 4),
        )

        if self.memory_manager is not None:
            reflection = {
                "goal": context.goal,
                "knowledge_insights": insight.to_dict(),
                "confidence": insight.confidence,
            }
            if hasattr(self.memory_manager, "store_reflection"):
                self.memory_manager.store_reflection(reflection)
        return insight
