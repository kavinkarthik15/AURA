from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from backend.services.python_code_executor import SecureExecutionUnavailable, execute_python_contract
from backend.services.python_skill_assessment_service import PythonSkillAssessmentService

ROOT = Path(__file__).resolve().parents[2]
FORM_A = ROOT / "research" / "17.16B" / "instruments" / "python_skill_form_a_v1.json"
FORM_B = ROOT / "research" / "17.16B" / "instruments" / "python_skill_form_b_v1.json"
BLUEPRINT = ROOT / "research" / "17.16B" / "instruments" / "python_skill_blueprint_v1.json"


def test_forms_load_and_hashes_match():
    form_a = PythonSkillAssessmentService.load_form(FORM_A)
    form_b = PythonSkillAssessmentService.load_form(FORM_B)
    assert form_a.form_id == "python_skill_form_a_v1"
    assert form_b.form_id == "python_skill_form_b_v1"
    assert form_a.form_version == "v1"
    assert form_b.form_version == "v1"
    assert form_a.assessment_hash == json.loads(FORM_A.read_text(encoding="utf-8"))["assessment_hash"]
    assert form_b.assessment_hash == json.loads(FORM_B.read_text(encoding="utf-8"))["assessment_hash"]


def test_blueprint_weights_sum_to_100():
    blueprint = json.loads(BLUEPRINT.read_text(encoding="utf-8"))
    assert sum(blueprint["domains"].values()) == 100


def test_raw_scoring_and_aura_mapping_are_deterministic():
    form = PythonSkillAssessmentService.load_form(FORM_A)
    responses = _correct_responses(form)
    result = PythonSkillAssessmentService.score_form(form, responses, execution_mode="DEVELOPMENT_RESTRICTED")
    assert result.raw_score == sum(item.maximum_points for item in form.items)
    assert result.aura_python_skill == 100.0
    assert result.aura_python_skill == result.raw_score
    assert "normalized_score" not in result.model_dump()


def test_partial_score_maps_to_same_aura_value_without_adjustment():
    form = PythonSkillAssessmentService.load_form(FORM_A)
    responses = _correct_responses(form)
    responses["a1"] = 0
    result = PythonSkillAssessmentService.score_form(form, responses, execution_mode="DEVELOPMENT_RESTRICTED")
    assert result.raw_score == 90
    assert result.aura_python_skill == 90


def test_missing_and_invalid_responses_are_recorded():
    form = PythonSkillAssessmentService.load_form(FORM_A)
    responses = {form.items[0].item_id: form.items[0].expected_answer}
    result = PythonSkillAssessmentService.score_form(form, responses, execution_mode="DEVELOPMENT_RESTRICTED")
    assert result.completed is False
    assert form.items[0].item_id not in result.invalid_items
    assert len(result.missing_items) >= 1
    assert result.completed is False


def test_code_output_items_score_deterministically():
    form = PythonSkillAssessmentService.load_form(FORM_B)
    responses = _correct_responses(form)
    result = PythonSkillAssessmentService.score_form(form, responses, execution_mode="DEVELOPMENT_RESTRICTED")
    assert result.raw_score == 100
    assert result.aura_python_skill == result.raw_score


def test_participant_scoring_defaults_to_secure_execution(monkeypatch):
    monkeypatch.delenv("AURA_SECURE_EXECUTION_IMAGE", raising=False)
    form = PythonSkillAssessmentService.load_form(FORM_A)

    with pytest.raises(SecureExecutionUnavailable):
        PythonSkillAssessmentService.score_form(form, _correct_responses(form))


def test_code_contract_execution_accepts_functionally_equivalent_code():
    form = PythonSkillAssessmentService.load_form(FORM_A)
    canonical = "def add(a, b):\n    return a + b\n"
    equivalent = "def add(a,b):\n    result = a + b\n    return result\n"
    contract = next(item.execution_contract for item in form.items if item.item_id == "a5")
    assert execute_python_contract(canonical, contract)
    assert execute_python_contract(equivalent, contract)


def test_invalid_required_code_response_makes_assessment_incomplete():
    form = PythonSkillAssessmentService.load_form(FORM_A)
    responses = _correct_responses(form)
    responses["a5"] = "def add(a, b):\n    return a - b\n"
    result = PythonSkillAssessmentService.score_form(form, responses, execution_mode="DEVELOPMENT_RESTRICTED")
    assert "a5" in result.invalid_items
    assert result.completed is False


def test_code_contract_rejects_wrong_syntax_runtime_and_timeout():
    contract = {
        "callable_name": "add",
        "test_cases": [{"args": [2, 3], "expected": 5}],
        "timeout_seconds": 1.0,
    }
    assert not execute_python_contract("def add(a, b):\n    return a - b\n", contract)
    assert not execute_python_contract("def add(a, b)\n    return a + b\n", contract)
    assert not execute_python_contract("def add(a, b):\n    raise ValueError('bad')\n", contract)
    assert not execute_python_contract(
        "def add(a, b):\n    while True:\n        pass\n",
        {**contract, "timeout_seconds": 1.0},
    )


def test_restricted_runner_rejects_direct_import_and_open():
    contract = {
        "callable_name": "add",
        "test_cases": [{"args": [2, 3], "expected": 5}],
        "timeout_seconds": 1.0,
    }
    for module in ("os", "pathlib", "sys", "subprocess", "socket"):
        assert not execute_python_contract(
            f"import {module}\ndef add(a, b):\n    return a + b\n",
            contract,
        )
    for restricted in (
        "open('x')",
        "__import__('os')",
        "eval('1 + 1')",
        "exec('x = 1')",
        "compile('1', '<x>', 'eval')",
        "globals()",
        "locals()",
    ):
        assert not execute_python_contract(
            f"def add(a, b):\n    return {restricted}\n",
            contract,
        )


def test_scoring_ignores_predictions_and_requires_submission_values():
    form = PythonSkillAssessmentService.load_form(FORM_A)
    result = PythonSkillAssessmentService.score_form(
        form,
        _correct_responses(form),
        execution_mode="DEVELOPMENT_RESTRICTED",
    )
    assert result.raw_score == sum(item.maximum_points for item in form.items)
    assert "base_prediction" not in result.model_dump()
    assert "mg_prediction" not in result.model_dump()


def test_counterbalanced_assignment_is_stable_and_rejects_wrong_form():
    assert tuple(inspect.signature(PythonSkillAssessmentService.assign_forms).parameters) == (
        "participant_id",
    )
    group_ids = {}
    for participant_id in ("pilot-user-ab", "pilot-user-ba"):
        assignment = PythonSkillAssessmentService.assign_forms(participant_id)
        group_ids.setdefault(assignment.assignment_group, participant_id)

    ab = PythonSkillAssessmentService.assign_forms(group_ids["AB"])
    ba = PythonSkillAssessmentService.assign_forms(group_ids["BA"])
    assert (ab.baseline_form, ab.followup_form) == (
        "python_skill_form_a_v1",
        "python_skill_form_b_v1",
    )
    assert (ba.baseline_form, ba.followup_form) == (
        "python_skill_form_b_v1",
        "python_skill_form_a_v1",
    )
    assert PythonSkillAssessmentService.assign_forms(group_ids["AB"]) == ab
    assert PythonSkillAssessmentService.assign_forms(group_ids["BA"]) == ba

    with pytest.raises(ValueError, match="does not match assigned form"):
        PythonSkillAssessmentService.validate_assigned_form(ab, "followup", ab.baseline_form)


def test_submitted_code_cannot_read_prediction_values_from_scorer():
    form = PythonSkillAssessmentService.load_form(FORM_A)
    contract = next(item.execution_contract for item in form.items if item.item_id == "a5")
    assert not execute_python_contract(
        "def add(a, b):\n    return base_prediction\n",
        contract,
    )
    assert not execute_python_contract(
        "def add(a, b):\n    return mg_prediction\n",
        contract,
    )


def _correct_responses(form):
    code_by_item = {
        "a5": "def add(a, b):\n    return a + b\n",
        "a6": "def double_list(values):\n    return [value * 2 for value in values]\n",
        "a9": "def sum_range_one_to_four():\n    total = 0\n    for value in range(1, 5):\n        total += value\n    return total\n",
        "b5": "def scale(x):\n    return x * 3\n",
        "b6": "def sorted_copy(values):\n    return sorted(values)\n",
        "b9": "def product_of_two():\n    return 2 * 6\n",
    }
    return {
        item.item_id: code_by_item[item.item_id]
        if item.item_id in code_by_item
        else item.expected_answer
        for item in form.items
    }
