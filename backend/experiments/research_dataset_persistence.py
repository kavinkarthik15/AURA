"""
17.0A Research Dataset Persistence

Save and load research datasets for reproducible research validation.
Supports JSON format for easy inspection and reuse.
"""

import json
from pathlib import Path
from typing import Optional
from backend.experiments.research_experience import ResearchDataset


class ResearchDatasetPersistence:
    """Handles saving and loading of research datasets."""

    def __init__(self, output_dir: str = "backend/experiments/data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save_dataset(self, dataset: ResearchDataset) -> Path:
        """
        Save dataset to JSON file.
        
        Args:
            dataset: ResearchDataset to save
            
        Returns:
            Path to saved file
        """
        filename = f"{dataset.dataset_id}.json"
        filepath = self.output_dir / filename

        # Serialize dataset
        data = {
            "dataset_id": dataset.dataset_id,
            "seed": dataset.seed,
            "training_size": dataset.training_size(),
            "held_out_size": dataset.held_out_size(),
            "training_experiences": [
                exp.model_dump() for exp in dataset.training_experiences
            ],
            "held_out_experiences": [
                exp.model_dump() for exp in dataset.held_out_experiences
            ],
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        return filepath

    def load_dataset(self, filepath_or_id: str) -> ResearchDataset:
        """
        Load dataset from JSON file.
        
        Args:
            filepath_or_id: Either a full path or just the dataset_id
                           (will look in output_dir)
            
        Returns:
            Loaded ResearchDataset
        """
        if filepath_or_id.endswith(".json"):
            filepath = Path(filepath_or_id)
        else:
            # Assume it's a dataset ID
            filepath = self.output_dir / f"{filepath_or_id}.json"

        if not filepath.exists():
            raise FileNotFoundError(f"Dataset not found: {filepath}")

        with open(filepath, "r") as f:
            data = json.load(f)

        # Reconstruct dataset
        from backend.experiments.research_experience import ResearchExperience

        training_experiences = [
            ResearchExperience(**exp) for exp in data["training_experiences"]
        ]
        held_out_experiences = [
            ResearchExperience(**exp) for exp in data["held_out_experiences"]
        ]

        return ResearchDataset(
            dataset_id=data["dataset_id"],
            seed=data["seed"],
            training_experiences=training_experiences,
            held_out_experiences=held_out_experiences,
        )

    def list_datasets(self) -> list[str]:
        """List all available datasets in output_dir."""
        return [f.stem for f in self.output_dir.glob("*.json")]

    def get_latest_dataset(self) -> Optional[ResearchDataset]:
        """Load the most recently saved dataset."""
        json_files = list(self.output_dir.glob("*.json"))
        if not json_files:
            return None
        latest = max(json_files, key=lambda p: p.stat().st_mtime)
        return self.load_dataset(latest.stem)
