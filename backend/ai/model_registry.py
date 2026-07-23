from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parent / "model_registry.json"


class ModelRegistry:
    def __init__(self, registry_path: Path | None = None) -> None:
        self.registry_path = registry_path or DEFAULT_REGISTRY_PATH
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

    def _load_registry(self) -> List[Dict[str, Any]]:
        if not self.registry_path.exists():
            return []
        with self.registry_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _save_registry(self, records: List[Dict[str, Any]]) -> None:
        with self.registry_path.open("w", encoding="utf-8") as handle:
            json.dump(records, handle, indent=4)

    def register_model(
        self,
        model_version: str,
        algorithm: str,
        dataset_size: int,
        mae: float,
        mse: float,
        r2: float,
        training_data_hash: str | None = None,
        dataset_version: str | None = None,
        parent_model: str | None = None,
        training_source: str | None = None,
        experience_count: int | None = None,
        accepted: bool | None = None,
        benchmark: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        record = {
            "model_version": model_version,
            "algorithm": algorithm,
            "dataset_size": dataset_size,
            "mae": mae,
            "mse": mse,
            "r2": r2,
            "training_data_hash": training_data_hash,
            "dataset_version": dataset_version or "v1",
            "parent_model": parent_model,
            "training_source": training_source,
            "experience_count": experience_count,
            "accepted": accepted,
            "benchmark": benchmark or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        records = self._load_registry()
        records.append(record)
        self._save_registry(records)
        return record

    def list_models(self) -> List[Dict[str, Any]]:
        return self._load_registry()

    def get_latest_model(self) -> Dict[str, Any] | None:
        records = self._load_registry()
        return records[-1] if records else None


registry = ModelRegistry()


def register_model_record(
    model_version: str,
    algorithm: str,
    dataset_size: int,
    mae: float,
    mse: float,
    r2: float,
    training_data_hash: str | None = None,
    dataset_version: str | None = None,
    parent_model: str | None = None,
    training_source: str | None = None,
    experience_count: int | None = None,
    accepted: bool | None = None,
    benchmark: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    return registry.register_model(
        model_version=model_version,
        algorithm=algorithm,
        dataset_size=dataset_size,
        mae=mae,
        mse=mse,
        r2=r2,
        training_data_hash=training_data_hash,
        dataset_version=dataset_version,
        parent_model=parent_model,
        training_source=training_source,
        experience_count=experience_count,
        accepted=accepted,
        benchmark=benchmark,
    )
