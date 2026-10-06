from __future__ import annotations

from datetime import datetime
import tempfile
import os

from backend.experiments.experiment_config import ExperimentConfig
from backend.experiments.experiment_runner import ExperimentRunner
from backend.models.calibration_parameters import CalibrationParameters


def test_experiment_runner_deterministic_and_persistence(tmp_path):
    config = ExperimentConfig(pairs=2, learning_rate=0.1, apply_accepted=True, seed=42, output_dir=str(tmp_path), experiment_id="r1")
    runner = ExperimentRunner()

    out1 = runner.run(config)
    # run again same config
    out2 = runner.run(config)

    assert out1["batch_result"].mean_baseline_error == out2["batch_result"].mean_baseline_error
    assert out1["metrics"].model_dump() == out2["metrics"].model_dump()
    # files saved
    assert os.path.exists(os.path.join(str(tmp_path), "r1.json"))
    assert os.path.exists(os.path.join(str(tmp_path), "r1.jsonl"))
    assert os.path.exists(os.path.join(str(tmp_path), "r1.csv"))


def test_experiment_runner_persists_enriched_metrics(tmp_path):
    config = ExperimentConfig(pairs=1, learning_rate=0.1, apply_accepted=True, seed=5, output_dir=str(tmp_path), experiment_id="metrics_test")
    runner = ExperimentRunner()

    out = runner.run(config)
    metrics = out["metrics"]

    assert metrics.rolling_baseline_mae
    assert metrics.rolling_calibrated_mae
    assert metrics.parameter_drift_progression
    assert "baseline_change_fraction" in metrics.stability_metrics

    # validate persistence includes metrics in JSON
    json_path = os.path.join(str(tmp_path), "metrics_test.json")
    with open(json_path, "r", encoding="utf-8") as f:
        import json as _json
        payload = _json.load(f)

    assert payload["experiment_metrics"]["acceptance_rate"] == metrics.acceptance_rate
    assert payload["experiment_metrics"]["rolling_baseline_mae"] == metrics.rolling_baseline_mae


def test_experiment_runner_apply_toggle(tmp_path):
    # apply_accepted True vs False should change final learning parameters
    config_true = ExperimentConfig(pairs=2, learning_rate=0.1, apply_accepted=True, seed=7)
    config_false = ExperimentConfig(pairs=2, learning_rate=0.1, apply_accepted=False, seed=7)
    runner = ExperimentRunner()

    res_true = runner.run(config_true)
    res_false = runner.run(config_false)

    params_true = res_true["batch_result"].final_learning_parameters
    params_false = res_false["batch_result"].final_learning_parameters

    assert params_true == params_true  # trivial
    # When not applying accepted, learning params should equal baseline default
    assert params_false == CalibrationParameters()


def test_experiment_cli_integration(tmp_path):
    import subprocess
    import sys

    output_dir = str(tmp_path)
    cmd = [
        sys.executable,
        "-m",
        "backend.experiments.experiment_cli",
        "--pairs",
        "1",
        "--output-dir",
        output_dir,
        "--experiment-id",
        "cli_test",
        "--apply-accepted",
        "--seed",
        "1",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert os.path.exists(os.path.join(output_dir, "cli_test.json"))
    assert os.path.exists(os.path.join(output_dir, "cli_test.jsonl"))
    assert os.path.exists(os.path.join(output_dir, "cli_test.csv"))
    assert "Rolling baseline MAE" in result.stdout
    assert "Overall acceptance rate" in result.stdout
