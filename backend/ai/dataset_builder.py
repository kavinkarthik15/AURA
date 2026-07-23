import json
from pathlib import Path
from typing import Any, Dict, List

from backend.services.experience_service import experience_service


DEFAULT_TRAINING_DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "training_data.json"


class DatasetBuilder:
    def __init__(self, output_file: Path | None = None) -> None:
        self.output_file = output_file or DEFAULT_TRAINING_DATA_FILE

    def _build_variants(self, experience: Any) -> List[Dict[str, Any]]:
        base_record = {
            "state_before": dict(experience.state_before),
            "action": experience.action,
            "state_after": dict(experience.state_after),
        }
        variants = [base_record]

        for offset in (2, 4):
            variant_after = dict(experience.state_after)
            for skill, value in variant_after.items():
                variant_after[skill] = min(100, int(value + offset))
            variants.append(
                {
                    "state_before": dict(experience.state_before),
                    "action": experience.action,
                    "state_after": variant_after,
                }
            )
        return variants

    def build_training_dataset(self) -> List[Dict[str, Any]]:
        experiences = experience_service.get_all_experiences()
        dataset: List[Dict[str, Any]] = []
        for experience in experiences:
            if not experience.state_before or not experience.state_after:
                continue
            dataset.extend(self._build_variants(experience))

        if len(dataset) < 100:
            for index, experience in enumerate(experience_service.get_all_experiences()[:3]):
                for offset in (6, 8):
                    synthetic_after = dict(experience.state_after)
                    for skill, value in synthetic_after.items():
                        synthetic_after[skill] = min(100, int(value + offset + index))
                    dataset.append(
                        {
                            "state_before": dict(experience.state_before),
                            "action": f"{experience.action} Synthetic",
                            "state_after": synthetic_after,
                        }
                    )

        return dataset[:120]

    def save_training_dataset(self, dataset: List[Dict[str, Any]] | None = None) -> Path:
        if dataset is None:
            dataset = self.build_training_dataset()
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "dataset_version": "v1",
            "records": dataset,
        }
        with self.output_file.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=4)
        return self.output_file


builder = DatasetBuilder()
