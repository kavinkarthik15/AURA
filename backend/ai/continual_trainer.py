import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from backend.ai.continual_dataset_builder import ContinualDatasetBuilder
from backend.ai.model_registry import ModelRegistry
from backend.ai.sequence_transition_model import SequenceTransitionModel
from backend.models.experience_log import ExperienceLog


class ContinualTrainer:
    def __init__(self, output_dir: str | None = None) -> None:
        self.output_dir = Path(output_dir or Path(__file__).resolve().parent)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.builder = ContinualDatasetBuilder()
        self.registry = ModelRegistry()

    def _serialize_dataset(self, samples: List[Dict[str, Any]]) -> str:
        payload = json.dumps(samples, sort_keys=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def train_candidate(self, experiences: List[ExperienceLog], base_dataset: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
        samples = self.builder.build_samples(experiences)
        if base_dataset:
            combined = list(base_dataset) + samples
        else:
            combined = samples

        model = SequenceTransitionModel()
        model.train(combined)

        model_path = self.output_dir / f"candidate_model_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.json"
        model_path.write_text(json.dumps(model.to_dict(), indent=2), encoding="utf-8")

        return {
            "model_version": f"v{len(self.registry.list_models()) + 1}",
            "model_path": str(model_path),
            "dataset_size": len(combined),
            "dataset_hash": self._serialize_dataset(combined),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
