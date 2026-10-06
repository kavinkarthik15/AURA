from __future__ import annotations

from copy import deepcopy
from typing import List, Optional, Dict, Any
import random
import os
from datetime import datetime

from backend.experiments.experiment_config import ExperimentConfig
from backend.models.decision_outcome import DecisionOutcome
from backend.models.calibration_parameters import CalibrationParameters
from backend.services.batch_closed_loop_evaluator import BatchClosedLoopEvaluator
from backend.services.experiment_metrics_calculator import ExperimentMetricsCalculator
from backend.services.experiment_recorder import ExperimentRecorder


class ExperimentRunner:
    def __init__(self) -> None:
        self.evaluator = BatchClosedLoopEvaluator()
        self.recorder = ExperimentRecorder()

    def generate_synthetic_experiences(self, pairs: int, seed: int = 0, noise_scale: float = 1.0) -> List[DecisionOutcome]:
        rng = random.Random(seed)
        experiences: List[DecisionOutcome] = []
        for i in range(pairs):
            base_pred = float(i * 10 + 10)
            # make actual deviate by small integer noise
            dev = rng.choice([-2, -1, 0, 1, 2]) * noise_scale
            actual_n = base_pred + dev

            n = DecisionOutcome(
                decision_id=f"s{i*2}",
                timestamp=datetime.utcnow(),
                initial_snapshot={"x": base_pred},
                selected_action="auto",
                predicted_state={"x": base_pred},
                predicted_trajectory_score=0.5,
                predicted_probability=0.5,
                predicted_risk=0.1,
                predicted_uncertainty=0.05,
                actual_state={"x": actual_n},
            )

            # next prediction uses different base
            base_pred2 = base_pred + 10.0
            dev2 = rng.choice([-2, -1, 0, 1, 2]) * noise_scale
            actual_n1 = base_pred2 + dev2
            n1 = DecisionOutcome(
                decision_id=f"s{i*2+1}",
                timestamp=datetime.utcnow(),
                initial_snapshot={"x": base_pred2},
                selected_action="auto",
                predicted_state={"x": base_pred2},
                predicted_trajectory_score=0.5,
                predicted_probability=0.5,
                predicted_risk=0.1,
                predicted_uncertainty=0.05,
                actual_state={"x": actual_n1},
            )

            experiences.extend([n, n1])

        return experiences

    def run(self, config: ExperimentConfig, experiences: Optional[List[DecisionOutcome]] = None) -> Dict[str, Any]:
        exp_id = config.experiment_id or f"exp_{int(datetime.utcnow().timestamp())}"
        timestamp = datetime.utcnow().isoformat()

        if experiences is None:
            experiences = self.generate_synthetic_experiences(config.pairs, seed=config.seed or 0, noise_scale=config.noise_scale)

        # run batch evaluator
        batch_result = self.evaluator.run(experiences, current_parameters=CalibrationParameters(), learning_rate=config.learning_rate, bounds=config.bounds, apply_accepted=config.apply_accepted)
        metrics = ExperimentMetricsCalculator.calculate(batch_result)

        # persist
        record = self.recorder.record_from_batch(exp_id, timestamp, batch_result, metrics=metrics.model_dump())

        if config.output_dir:
            os.makedirs(config.output_dir, exist_ok=True)
            json_path = os.path.join(config.output_dir, f"{exp_id}.json")
            jsonl_path = os.path.join(config.output_dir, f"{exp_id}.jsonl")
            csv_path = os.path.join(config.output_dir, f"{exp_id}.csv")
            with open(json_path, "w", encoding="utf-8") as f:
                self.recorder.save_json(record, f)
            with open(jsonl_path, "w", encoding="utf-8") as f:
                self.recorder.save_jsonl(record, f)
            with open(csv_path, "w", encoding="utf-8", newline="") as f:
                self.recorder.save_csv(record, f)

        return {"experiment_id": exp_id, "timestamp": timestamp, "batch_result": batch_result, "record": record, "metrics": metrics}
