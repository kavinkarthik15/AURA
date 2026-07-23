from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Any, Dict, Iterable, List

import numpy as np
from sklearn.ensemble import RandomForestRegressor

from backend.ai.action_encoder import encoder
from backend.ai.model_configs import FEATURES, MODEL_VERSION, TARGETS
from backend.ai.model_errors import ModelNotFoundError


class SequenceTransitionModel:
    """Sequence-aware RandomForestRegressor for state transition prediction."""

    DEFAULT_MODEL_PATH = Path(__file__).resolve().parent / "saved_models" / "sequence_model.pkl"

    def __init__(self, model: RandomForestRegressor | None = None) -> None:
        self.model = model or RandomForestRegressor(
            n_estimators=300,
            random_state=42,
            n_jobs=-1,
        )
        self.feature_names = list(FEATURES)
        self.target_names = list(TARGETS)

    def _normalize_state(self, current_state: Dict[str, Any]) -> Dict[str, float]:
        normalized: Dict[str, float] = {}
        for feature in self.feature_names:
            value = current_state.get(feature, 0)
            normalized[feature] = float(value or 0)
        return normalized

    def _history_counts(self, history: List[str]) -> Dict[str, int]:
        counters = {
            "project": 0,
            "learning": 0,
            "competition": 0,
            "experience": 0,
            "practice": 0,
        }
        for action in history:
            lowered = action.lower()
            if "project" in lowered or "build" in lowered or "create" in lowered:
                counters["project"] += 1
            if "course" in lowered or "study" in lowered or "learn" in lowered:
                counters["learning"] += 1
            if "hackathon" in lowered or "contest" in lowered:
                counters["competition"] += 1
            if "internship" in lowered or "work" in lowered:
                counters["experience"] += 1
            if "dsa" in lowered or "leetcode" in lowered:
                counters["practice"] += 1
        return counters

    def _build_action_feature(self, action: str) -> List[float]:
        return encoder.encode_action(action)

    def _build_feature_vector(self, current_state: Dict[str, Any], history: List[str], action: str) -> List[float]:
        normalized_state = self._normalize_state(current_state)
        state_vector = [normalized_state.get(feature, 0.0) for feature in self.feature_names]

        history_counts = self._history_counts(history)
        history_vector = [
            float(history_counts["project"]),
            float(history_counts["learning"]),
            float(history_counts["competition"]),
            float(history_counts["experience"]),
            float(history_counts["practice"]),
        ]

        action_vector = self._build_action_feature(action)
        combined = state_vector + history_vector + action_vector
        return combined

    def _build_training_arrays(self, dataset: Iterable[Dict[str, Any]]) -> tuple[List[List[float]], List[List[float]]]:
        features: List[List[float]] = []
        targets: List[List[float]] = []

        for record in dataset:
            current_state = record.get("current_state", {})
            history = record.get("action_history", [])
            action = record.get("next_action", "")
            target_delta = record.get("target_delta", {})

            features.append(self._build_feature_vector(current_state, history, action))
            targets.append([
                float(target_delta.get("python_growth", 0.0)),
                float(target_delta.get("machine_learning_growth", 0.0)),
                float(target_delta.get("dsa_growth", 0.0)),
                float(target_delta.get("project_growth", 0.0)),
            ])

        return features, targets

    def train(self, dataset: Iterable[Dict[str, Any]]) -> "SequenceTransitionModel":
        X, y = self._build_training_arrays(dataset)
        self.model.fit(X, y)
        return self

    def predict(self, current_state: Dict[str, Any], history: List[str], action: str) -> Dict[str, float]:
        vector = self._build_feature_vector(current_state, history, action)
        prediction = self.model.predict([vector])[0]
        return {
            "python_growth": float(prediction[0]),
            "machine_learning_growth": float(prediction[1]),
            "dsa_growth": float(prediction[2]),
            "project_growth": float(prediction[3]),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feature_names": self.feature_names,
            "target_names": self.target_names,
            "n_estimators": getattr(self.model, "n_estimators", None),
            "random_state": getattr(self.model, "random_state", None),
        }

    def save_model(self, output_path: Path | None = None) -> Path:
        target_path = output_path or self.DEFAULT_MODEL_PATH
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with target_path.open("wb") as handle:
            pickle.dump(self, handle)
        return target_path

    @classmethod
    def load_model(cls, model_path: Path | None = None) -> "SequenceTransitionModel":
        target_path = model_path or cls.DEFAULT_MODEL_PATH
        if not target_path.exists():
            raise ModelNotFoundError(
                f"SequenceTransitionModel artifact was not found at {target_path}. "
                "Train the model first or provide a valid model path."
            )
        with target_path.open("rb") as handle:
            return pickle.load(handle)


def load_sequence_dataset(dataset_path: Path | None = None) -> List[Dict[str, Any]]:
    target_path = dataset_path or Path(__file__).resolve().parents[1] / "data" / "sequence_training_data.json"
    with target_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if isinstance(payload, dict):
        records = payload.get("records", payload.get("data", []))
        return records
    return payload
