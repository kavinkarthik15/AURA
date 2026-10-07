from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "17_16B_PILOT_PROTOCOL_CONFIG.json"
INSTRUMENTS = ROOT / "research" / "17.16B" / "instruments"
FORM_A_PATH = INSTRUMENTS / "python_skill_form_a_v1.json"
FORM_B_PATH = INSTRUMENTS / "python_skill_form_b_v1.json"
BLUEPRINT_PATH = INSTRUMENTS / "python_skill_blueprint_v1.json"
MODULE_PATH = ROOT / "research" / "17.16B" / "action" / "python_practice_core_v1.json"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_hash(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _artifact_hash(payload: dict, field: str) -> str:
    return _canonical_hash({key: value for key, value in payload.items() if key != field})


def _computed_domain_points(form: dict) -> dict[str, int]:
    points: defaultdict[str, int] = defaultdict(int)
    for item in form["items"]:
        points[item["domain"]] += item["maximum_points"]
    return dict(points)


def _all_mapping_keys(value: object) -> list[str]:
    if isinstance(value, dict):
        return [str(key) for key in value] + [
            key for nested in value.values() for key in _all_mapping_keys(nested)
        ]
    if isinstance(value, list):
        return [key for nested in value for key in _all_mapping_keys(nested)]
    return []


def test_actual_form_points_match_blueprint_and_score_mapping():
    expected = {
        "variables_and_types": 20,
        "control_flow": 20,
        "functions": 20,
        "collections": 20,
        "debugging_reasoning": 10,
        "problem_solving": 10,
    }
    for form_path in (FORM_A_PATH, FORM_B_PATH):
        form = _read_json(form_path)
        assert len(form["items"]) == 10
        assert all(item["maximum_points"] == 10 for item in form["items"])
        assert _computed_domain_points(form) == expected
        assert sum(item["maximum_points"] for item in form["items"]) == 100
    assert _read_json(BLUEPRINT_PATH)["domains"] == expected


def test_artifact_hashes_bind_to_protocol_hash():
    artifacts = {
        "blueprint": _read_json(BLUEPRINT_PATH),
        "form_a": _read_json(FORM_A_PATH),
        "form_b": _read_json(FORM_B_PATH),
        "module": _read_json(MODULE_PATH),
    }
    stored_fields = {
        "blueprint": ("assessment_hash", "blueprint_hash"),
        "form_a": ("assessment_hash", "form_a_hash"),
        "form_b": ("assessment_hash", "form_b_hash"),
        "module": ("module_hash", "module_hash"),
    }
    config = _read_json(CONFIG_PATH)
    bindings = config["artifact_bindings"]

    for artifact_name, (stored_hash_field, binding_hash_field) in stored_fields.items():
        artifact = artifacts[artifact_name]
        expected_hash = _artifact_hash(artifact, stored_hash_field)
        assert artifact[stored_hash_field] == expected_hash
        assert bindings[artifact_name][binding_hash_field] == expected_hash
    assert bindings["blueprint"]["blueprint_id"] == artifacts["blueprint"]["blueprint_id"]
    assert bindings["blueprint"]["blueprint_version"] == artifacts["blueprint"]["blueprint_version"]
    assert artifacts["blueprint"]["form_a_id"] == artifacts["form_a"]["form_id"]
    assert artifacts["blueprint"]["form_b_id"] == artifacts["form_b"]["form_id"]
    for name in ("form_a", "form_b"):
        assert bindings[name][f"{name}_id"] == artifacts[name]["form_id"]
        assert bindings[name][f"{name}_version"] == artifacts[name]["form_version"]
    assert bindings["module"]["module_id"] == artifacts["module"]["module_id"]
    assert bindings["module"]["module_version"] == artifacts["module"]["module_version"]

    protocol_payload = {key: value for key, value in config.items() if key != "protocol_hash"}
    assert config["protocol_hash"] == _canonical_hash(protocol_payload)

    for artifact_name, (_, binding_hash_field) in stored_fields.items():
        changed = json.loads(json.dumps(config))
        changed["artifact_bindings"][artifact_name][binding_hash_field] = "0" * 64
        changed_payload = {key: value for key, value in changed.items() if key != "protocol_hash"}
        assert _canonical_hash(changed_payload) != config["protocol_hash"]


def test_protocol_remains_unapproved_and_collection_blocked():
    config = _read_json(CONFIG_PATH)
    checkpoint = _read_json(ROOT / "RESEARCH_CHECKPOINT_17_16B_DESIGN.json")
    assert config["pilot_owner_approval"] is False
    assert config["measurement_instrument_ready"] is False
    assert config["action_module_ready"] is False
    assert config["collection_ready"] is False
    quality_field = "quality" + "_threshold"
    secondary_horizon_field = "secondary_horizon_" + "days"
    assert all(quality_field not in key for key in _all_mapping_keys(config))
    assert config["observation_horizon"]["primary_horizon_days"] == 7
    assert config["observation_horizon"]["allowed_timing_window_days"] == {"start": 7, "end": 10}
    assert secondary_horizon_field not in config["observation_horizon"]
    assert "assessment_validity_rule" in config["measurement_instrument"]
    assert config["version_freeze_policy"]["before_owner_approval"].startswith("v1 artifacts may")
    assert "v2" in config["version_freeze_policy"]["subsequent_changes"]
    assert checkpoint["protocol_config"]["protocol_hash"] == config["protocol_hash"]
    assert checkpoint["eligible_real_outcomes"] == 0
    gates = config["final_technical_approval_gate"]
    assert gates["technical_artifacts_complete"] is False
    assert gates["security_execution_gate"] == "FAIL"
    assert gates["hash_binding_gate"] == "PASS"
    assert gates["measurement_logic_gate"] == "PASS"
    assert gates["action_module_gate"] == "PASS"
    assert gates["protocol_integrity_gate"] == "PASS"
    assert gates["recommendation"] == "REVISIONS_REQUIRED"
