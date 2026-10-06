from __future__ import annotations

import io
from datetime import datetime

from backend.models.calibration_parameters import CalibrationParameters
from backend.services.batch_closed_loop_evaluator import BatchClosedLoopEvaluator
from backend.services.experiment_recorder import ExperimentRecorder


def test_experiment_record_json_roundtrip(tmp_path):
    evaluator = BatchClosedLoopEvaluator()
    # simple pair
    from backend.models.decision_outcome import DecisionOutcome

    from datetime import datetime as dt

    n = DecisionOutcome(
        decision_id="x1",
        timestamp=dt.utcnow(),
        initial_snapshot={"x": 10},
        selected_action="a",
        predicted_state={"x": 10},
        predicted_trajectory_score=0.1,
        predicted_probability=0.1,
        predicted_risk=0.0,
        predicted_uncertainty=0.0,
        actual_state={"x": 12},
    )
    n1 = DecisionOutcome(
        decision_id="x2",
        timestamp=dt.utcnow(),
        initial_snapshot={"x": 20},
        selected_action="a",
        predicted_state={"x": 20},
        predicted_trajectory_score=0.1,
        predicted_probability=0.1,
        predicted_risk=0.0,
        predicted_uncertainty=0.0,
        actual_state={"x": 21},
    )

    res = evaluator.run([n, n1], current_parameters=CalibrationParameters(), learning_rate=0.1)

    recorder = ExperimentRecorder()
    record = recorder.record_from_batch("exp1", datetime.utcnow().isoformat(), res)

    # json roundtrip in-memory
    buf = io.StringIO()
    recorder.save_json(record, buf)
    buf.seek(0)
    loaded = recorder.load_json(buf)

    assert loaded.experiment_id == record.experiment_id
    assert loaded.batch_size == record.batch_size
    assert loaded.final_learning_parameters == record.final_learning_parameters


def test_experiment_csv_and_jsonl(tmp_path):
    evaluator = BatchClosedLoopEvaluator()
    from backend.models.decision_outcome import DecisionOutcome
    from datetime import datetime as dt

    n = DecisionOutcome(
        decision_id="y1",
        timestamp=dt.utcnow(),
        initial_snapshot={"x": 1},
        selected_action="a",
        predicted_state={"x": 1},
        predicted_trajectory_score=0.1,
        predicted_probability=0.1,
        predicted_risk=0.0,
        predicted_uncertainty=0.0,
        actual_state={"x": 2},
    )
    n1 = DecisionOutcome(
        decision_id="y2",
        timestamp=dt.utcnow(),
        initial_snapshot={"x": 2},
        selected_action="a",
        predicted_state={"x": 2},
        predicted_trajectory_score=0.1,
        predicted_probability=0.1,
        predicted_risk=0.0,
        predicted_uncertainty=0.0,
        actual_state={"x": 3},
    )

    res = evaluator.run([n, n1], current_parameters=CalibrationParameters(), learning_rate=0.1)
    recorder = ExperimentRecorder()
    record = recorder.record_from_batch("exp2", datetime.utcnow().isoformat(), res)

    # write csv
    csv_path = tmp_path / "exp.csv"
    with open(csv_path, "w", encoding="utf-8") as f:
        recorder.save_csv(record, f)

    # write jsonl
    jsonl_path = tmp_path / "exp.jsonl"
    with open(jsonl_path, "w", encoding="utf-8") as f:
        recorder.save_jsonl(record, f)

    # basic checks
    assert csv_path.exists()
    assert jsonl_path.exists()
    # csv has at least header and one line
    with open(csv_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) >= 2

    with open(jsonl_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) >= 2
