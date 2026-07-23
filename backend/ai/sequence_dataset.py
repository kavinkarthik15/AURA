from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

from backend.ai.action_encoder import encoder
from backend.ai.transition_model import load_training_dataset


DEFAULT_SEQUENCE_DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "sequence_training_data.json"


class SequenceDatasetBuilder:
    def __init__(self, output_file: Path | None = None) -> None:
        self.output_file = output_file or DEFAULT_SEQUENCE_DATA_FILE

    def build_history_features(self, history: List[str]) -> List[float]:
        if not history:
            return [0.0] * len(encoder.vocabulary)

        vectors = [encoder.encode_action(action) for action in history]
        return np.mean(vectors, axis=0).tolist()

    def _build_sequences_from_transitions(self, transitions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        sequences: List[Dict[str, Any]] = []

        for index in range(len(transitions)):
            current_record = transitions[index]
            history = [record.get("action", "") for record in transitions[:index]]
            next_action = current_record.get("action", "")
            current_state = dict(current_record.get("state_before", {}))
            state_after = dict(current_record.get("state_after", {}))
            target_delta = {
                "python_growth": float(state_after.get("python", 0) - current_state.get("python", 0)),
                "machine_learning_growth": float(state_after.get("machine_learning", 0) - current_state.get("machine_learning", 0)),
                "dsa_growth": float(state_after.get("dsa", 0) - current_state.get("dsa", 0)),
                "project_growth": float(state_after.get("projects", 0) - current_state.get("projects", 0)),
            }

            sequences.append(
                {
                    "current_state": current_state,
                    "action_history": history,
                    "history_features": self.build_history_features(history),
                    "next_action": next_action,
                    "target_delta": target_delta,
                }
            )

        return sequences

    def build_sequence_dataset(self) -> List[Dict[str, Any]]:
        transitions = load_training_dataset()
        sequences = self._build_sequences_from_transitions(transitions)
        return sequences[:120]

    def save_sequence_dataset(self, dataset: List[Dict[str, Any]] | None = None) -> Path:
        if dataset is None:
            dataset = self.build_sequence_dataset()
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "dataset_version": "v1",
            "records": dataset,
        }
        with self.output_file.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=4)
        return self.output_file


builder = SequenceDatasetBuilder()
