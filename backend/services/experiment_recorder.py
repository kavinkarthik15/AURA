from __future__ import annotations

import csv
import json
from copy import deepcopy
from typing import IO, Dict, Any

from backend.models.batch_closed_loop_result import BatchClosedLoopResult
from backend.models.experiment_record import ExperimentRecord


class ExperimentRecorder:
    """Persistence helpers for batch closed-loop experiments.

    Keeps evaluator independent of storage. Provides JSON, JSONL, and CSV exports.
    """

    def record_from_batch(self, experiment_id: str, timestamp: str, batch_result: BatchClosedLoopResult, metrics: dict | None = None) -> ExperimentRecord:
        if metrics is not None:
            metadata = deepcopy(batch_result.metadata)
            metadata["experiment_metrics"] = metrics
            record = ExperimentRecord.from_batch_result(experiment_id, timestamp, batch_result)
            record.metadata = metadata
            record.experiment_metrics = metrics
            return record
        return ExperimentRecord.from_batch_result(experiment_id, timestamp, batch_result)

    def save_json(self, record: ExperimentRecord, fp: IO[str]) -> None:
        json.dump(record.model_dump(), fp, indent=2)

    def load_json(self, fp: IO[str]) -> ExperimentRecord:
        data = json.load(fp)
        return ExperimentRecord(**data)

    def save_jsonl(self, record: ExperimentRecord, fp: IO[str]) -> None:
        # first line: metadata
        payload = {"experiment_id": record.experiment_id, "metadata": record.model_dump()["metadata"]}
        fp.write(json.dumps(payload) + "\n")
        for step in record.steps:
            fp.write(json.dumps(step.model_dump()) + "\n")

    def save_csv(self, record: ExperimentRecord, fp: IO[str]) -> None:
        fieldnames = [
            "experiment_id",
            "index",
            "baseline_future_error",
            "calibrated_future_error",
            "error_improvement",
            "helped",
            "calibration_proposal",
            "parameter_changes",
            "experiment_metrics",
        ]
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        metrics_json = json.dumps(record.experiment_metrics or {})
        for step in record.steps:
            writer.writerow(
                {
                    "experiment_id": record.experiment_id,
                    "index": step.index,
                    "baseline_future_error": step.baseline_future_error,
                    "calibrated_future_error": step.calibrated_future_error,
                    "error_improvement": step.error_improvement,
                    "helped": step.helped,
                    "calibration_proposal": json.dumps(step.calibration_proposal),
                    "parameter_changes": json.dumps(step.parameter_changes),
                    "experiment_metrics": metrics_json,
                }
            )
