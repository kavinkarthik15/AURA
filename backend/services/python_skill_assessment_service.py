from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from backend.models.python_skill_assessment import (
    AssessmentAssignment,
    AssessmentForm,
    AssessmentResult,
    compute_sha256,
)
from backend.services.python_code_executor import execute_python_contract, get_secure_execution_backend


class PythonSkillAssessmentService:
    @staticmethod
    def assign_forms(participant_id: str) -> AssessmentAssignment:
        if not participant_id:
            raise ValueError("participant_id must not be empty")
        group = "AB" if hashlib.sha256(participant_id.encode("utf-8")).digest()[0] & 1 == 0 else "BA"
        return AssessmentAssignment(
            participant_id=participant_id,
            assignment_group=group,
            baseline_form="python_skill_form_a_v1" if group == "AB" else "python_skill_form_b_v1",
            followup_form="python_skill_form_b_v1" if group == "AB" else "python_skill_form_a_v1",
            assignment_method="sha256_user_id_first_bit",
        )

    @staticmethod
    def validate_assigned_form(
        assignment: AssessmentAssignment,
        phase: str,
        submitted_form_id: str,
    ) -> None:
        if phase == "baseline":
            expected_form = assignment.baseline_form
        elif phase == "followup":
            expected_form = assignment.followup_form
        else:
            raise ValueError("phase must be 'baseline' or 'followup'")
        if submitted_form_id != expected_form:
            raise ValueError(f"{phase} form does not match assigned form")

    @staticmethod
    def load_form(path: str | Path) -> AssessmentForm:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        form = AssessmentForm.model_validate(payload)
        canonical = {key: value for key, value in payload.items() if key != "assessment_hash"}
        if form.assessment_hash != compute_sha256(canonical):
            raise ValueError("assessment form hash mismatch")
        return form

    @staticmethod
    def score_form(
        form: AssessmentForm,
        responses: dict[str, Any],
        *,
        execution_mode: str = "SECURE_CONTAINER",
    ) -> AssessmentResult:
        if not isinstance(responses, dict):
            raise TypeError("responses must be a mapping of item ids to answer values")

        raw_score = 0
        missing_items: list[str] = []
        invalid_items: list[str] = []
        executor = get_secure_execution_backend() if execution_mode == "SECURE_CONTAINER" else None

        for item in form.items:
            answer = responses.get(item.item_id)
            if answer is None:
                missing_items.append(item.item_id)
                continue
            if PythonSkillAssessmentService._matches(
                item,
                answer,
                item.expected_answer,
                execution_mode=execution_mode,
                executor=executor,
            ):
                raw_score += item.maximum_points
            else:
                invalid_items.append(item.item_id)

        aura_python_skill = float(raw_score)
        invalid_required_items = {
            item.item_id for item in form.items if item.required and item.item_id in invalid_items
        }
        missing_required_items = {
            item.item_id for item in form.items if item.required and item.item_id in missing_items
        }

        return AssessmentResult(
            assessment_id=(
                "assessment_"
                + hashlib.sha256(f"{form.form_id}:{form.form_version}".encode("utf-8")).hexdigest()
            ),
            participant_id="unknown-participant",
            episode_id="unknown-episode",
            pilot_id="17_16B_python_skill_pilot_v1",
            form_id=form.form_id,
            form_version=form.form_version,
            raw_score=raw_score,
            aura_python_skill=aura_python_skill,
            completed=not missing_required_items and not invalid_required_items,
            missing_items=missing_items,
            invalid_items=invalid_items,
            instrument_hash=form.assessment_hash,
        )

    @staticmethod
    def _matches(
        item: Any,
        submitted: Any,
        expected: Any,
        *,
        execution_mode: str,
        executor: Any = None,
    ) -> bool:
        if item.scoring_method in {"exact_match", "multiple_choice"}:
            return PythonSkillAssessmentService._normalize_value(submitted) == PythonSkillAssessmentService._normalize_value(expected)
        if item.scoring_method == "true_false":
            return bool(submitted) is bool(expected)
        if item.scoring_method == "code_output":
            contract = getattr(item, "execution_contract", None)
            if isinstance(submitted, str) and isinstance(contract, dict):
                return execute_python_contract(
                    submitted,
                    contract,
                    mode=execution_mode,
                    backend=executor,
                )
            return False
        return False

    @staticmethod
    def _normalize_value(value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().lower()
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return value
        if isinstance(value, list):
            return [PythonSkillAssessmentService._normalize_value(item) for item in value]
        return value
