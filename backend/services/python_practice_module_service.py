from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.models.python_practice_module import PythonPracticeCompletion, PythonPracticeModule, compute_sha256
from backend.services.python_code_executor import execute_python_contract, get_secure_execution_backend


class PythonPracticeModuleService:
    @staticmethod
    def load_module(path: str | Path) -> PythonPracticeModule:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        module = PythonPracticeModule.model_validate(payload)
        canonical = {key: value for key, value in payload.items() if key != "module_hash"}
        if module.module_hash != compute_sha256(canonical):
            raise ValueError("practice module hash mismatch")
        return module

    @staticmethod
    def evaluate_completion(
        module: PythonPracticeModule,
        exercise_results: dict[str, dict[str, Any]],
        *,
        participant_id: str,
        started_at: datetime,
        completed_at: datetime,
        execution_mode: str = "SECURE_CONTAINER",
    ) -> PythonPracticeCompletion:
        if not participant_id.strip():
            raise ValueError("participant_id must be non-empty")
        if started_at.tzinfo is None or started_at.utcoffset() is None:
            raise ValueError("started_at must include a timezone")
        if completed_at.tzinfo is None or completed_at.utcoffset() is None:
            raise ValueError("completed_at must include a timezone")
        if completed_at <= started_at:
            raise ValueError("completed_at must be after started_at")
        if execution_mode not in {"DEVELOPMENT_RESTRICTED", "SECURE_CONTAINER"}:
            raise ValueError(f"unsupported code execution mode: {execution_mode}")
        required_passed = 0
        exercise_attempts: dict[str, int] = {}
        exercise_results_out: dict[str, bool] = {}
        executor = get_secure_execution_backend() if execution_mode == "SECURE_CONTAINER" else None

        for exercise_id in module.required_exercises:
            exercise = next((item for item in module.exercises if item.exercise_id == exercise_id), None)
            result = exercise_results.get(exercise_id, {})
            attempts = int(result.get("attempts", 0))
            submission = result.get("submission") or result.get("code")
            passed = False
            if attempts > 0 and submission is not None and exercise is not None and exercise.execution_contract is not None:
                passed = execute_python_contract(
                    submission,
                    exercise.execution_contract,
                    mode=execution_mode,
                    backend=executor,
                )
            elif submission is not None and exercise is not None:
                passed = (
                    attempts > 0
                    and PythonPracticeModuleService._normalize_value(submission)
                    == PythonPracticeModuleService._normalize_value(exercise.expected_answer)
                )
            exercise_attempts[exercise_id] = attempts
            exercise_results_out[exercise_id] = passed
            if passed:
                required_passed += 1

        max_retries = int(module.retry_policy.get("max_retries", 0))
        dirty_retry = any(
            exercise_attempts.get(exercise_id, 0) > max_retries + 1
            for exercise_id in module.required_exercises
        )
        completed = required_passed >= int(module.completion_threshold["required_exercises_to_pass"]) and not dirty_retry

        identity = (
            f"{module.module_id}:{module.module_version}:{participant_id}:"
            f"{started_at.astimezone(timezone.utc).isoformat()}:"
            f"{completed_at.astimezone(timezone.utc).isoformat()}"
        )
        completion_id = f"module_completion_{hashlib.sha256(identity.encode('utf-8')).hexdigest()}"
        return PythonPracticeCompletion(
            completion_id=completion_id,
            participant_id=participant_id,
            module_id=module.module_id,
            module_version=module.module_version,
            module_hash=module.module_hash,
            started_at=started_at.astimezone(timezone.utc),
            completed_at=completed_at.astimezone(timezone.utc),
            required_exercises_passed=required_passed,
            completion_status="complete" if completed else "incomplete",
            completion_evidence_id=f"evidence:{module.module_id}:{completion_id}",
            exercise_attempts=exercise_attempts,
            exercise_results=exercise_results_out,
        )

    @staticmethod
    def _normalize_value(value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().lower()
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return value
        if isinstance(value, list):
            return [PythonPracticeModuleService._normalize_value(item) for item in value]
        return value
