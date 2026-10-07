from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from backend.services.python_code_executor import SecureExecutionUnavailable
from backend.services.python_practice_module_service import PythonPracticeModuleService

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "research" / "17.16B" / "action" / "python_practice_core_v1.json"


def test_practice_module_loads_and_hash_matches():
    module = PythonPracticeModuleService.load_module(MODULE_PATH)
    assert module.module_id == "PYTHON_PRACTICE_CORE_V1"
    assert module.module_version == "v1"
    assert module.completion_threshold["required_exercises_to_pass"] >= 1
    assert module.module_hash == json.loads(MODULE_PATH.read_text(encoding="utf-8"))["module_hash"]


def test_module_completion_logic_is_deterministic():
    module = PythonPracticeModuleService.load_module(MODULE_PATH)
    results = _passing_results(module)
    completion = _evaluate(module, results)
    assert completion.completion_status == "complete"
    assert completion.required_exercises_passed >= module.completion_threshold["required_exercises_to_pass"]
    assert completion.completion_evidence_id


def test_completion_id_is_stable_for_identical_completion_inputs():
    module = PythonPracticeModuleService.load_module(MODULE_PATH)
    results = _passing_results(module)

    first = _evaluate(module, results)
    second = _evaluate(module, results)

    assert first.completion_id == second.completion_id


def test_participant_module_execution_defaults_to_secure_backend(monkeypatch):
    monkeypatch.delenv("AURA_SECURE_EXECUTION_IMAGE", raising=False)
    module = PythonPracticeModuleService.load_module(MODULE_PATH)
    started_at = datetime(2026, 1, 1, tzinfo=timezone.utc)

    with pytest.raises(SecureExecutionUnavailable):
        PythonPracticeModuleService.evaluate_completion(
            module,
            _passing_results(module),
            participant_id="participant-1",
            started_at=started_at,
            completed_at=started_at + timedelta(minutes=5),
        )


def test_retry_policy_is_enforced():
    module = PythonPracticeModuleService.load_module(MODULE_PATH)
    results = _passing_results(module)
    results[module.required_exercises[0]]["attempts"] = 2
    completion = _evaluate(module, results)
    assert completion.completion_status == "complete"

    results[module.required_exercises[0]]["attempts"] = 3
    completion = _evaluate(module, results)
    assert completion.completion_status == "incomplete"


def test_module_domain_labels_match_exercise_content():
    module = PythonPracticeModuleService.load_module(MODULE_PATH)
    domain_by_id = {exercise.exercise_id: exercise.domain for exercise in module.exercises}
    assert domain_by_id == {
        "exercise_variables": "variables_and_types",
        "exercise_loops": "control_flow",
        "exercise_functions": "functions",
        "exercise_collections": "collections",
        "exercise_debugging": "debugging_reasoning",
    }
    assert set(module.competency_domains) == set(domain_by_id.values())
    assert set(module.exercise_ids) == set(domain_by_id)
    assert set(module.required_exercises) == {
        exercise.exercise_id for exercise in module.exercises if exercise.required
    }
    assert set(module.optional_exercises) == {
        exercise.exercise_id for exercise in module.exercises if not exercise.required
    }
    assert module.retry_policy == {"max_retries": 1, "retry_only_required": True}


def test_module_code_is_scored_by_behavior_not_passed_flag():
    module = PythonPracticeModuleService.load_module(MODULE_PATH)
    exercise_id = "exercise_variables"
    equivalent = "def add(a,b):\n    result = a + b\n    return result\n"
    results = _passing_results(module)
    results[exercise_id] = {"attempts": 1, "submission": equivalent, "passed": False}
    completion = _evaluate(module, results)
    assert completion.exercise_results[exercise_id] is True

    results[exercise_id] = {"attempts": 1, "submission": "def add(a, b):\n    return a-b\n", "passed": True}
    completion = _evaluate(module, results)
    assert completion.exercise_results[exercise_id] is False
    assert completion.completion_status == "incomplete"


def test_module_cannot_be_completed_by_claiming_passed_without_submission():
    module = PythonPracticeModuleService.load_module(MODULE_PATH)
    results = {
        exercise_id: {"attempts": 1, "passed": True}
        for exercise_id in module.required_exercises
    }
    completion = _evaluate(module, results)
    assert completion.completion_status == "incomplete"


def test_module_performance_is_not_used_as_outcome_value():
    module = PythonPracticeModuleService.load_module(MODULE_PATH)
    results = _passing_results(module)
    completion = _evaluate(module, results)
    assert completion.completion_status == "complete"
    assert "observed_outcome" not in completion.model_dump(mode="json")


def _passing_results(module):
    submissions = {
        "exercise_variables": "def add(a,b):\n    return a+b\n",
        "exercise_loops": "def sum_first_three():\n    return sum(range(1, 4))\n",
        "exercise_functions": "def double(x):\n    return x * 2\n",
    }
    return {
        exercise_id: {"attempts": 1, "submission": submissions[exercise_id]}
        for exercise_id in module.required_exercises
    }


def _evaluate(module, results):
    started_at = datetime(2026, 10, 7, 10, tzinfo=timezone.utc)
    return PythonPracticeModuleService.evaluate_completion(
        module,
        results,
        participant_id="test-participant",
        started_at=started_at,
        completed_at=started_at + timedelta(minutes=10),
        execution_mode="DEVELOPMENT_RESTRICTED",
    )
