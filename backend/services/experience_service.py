import json
from pathlib import Path
from typing import Any, Dict, List

from backend.models.experience import Experience
from backend.services.experience_processor import build_experience_delta


DEFAULT_EXPERIENCES_FILE = Path(__file__).resolve().parents[1] / "data" / "experiences.json"
DEFAULT_SYNTHETIC_EXPERIENCES_FILE = Path(__file__).resolve().parents[1] / "data" / "synthetic_experiences.json"


class ExperienceService:
    def __init__(self, file_path: Path | None = None) -> None:
        self.file_path = file_path or DEFAULT_EXPERIENCES_FILE

    def load_experiences(self) -> List[Experience]:
        if not self.file_path.exists():
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            self.file_path.write_text("[]", encoding="utf-8")

        with self.file_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)

        synthetic_data: List[Dict[str, Any]] = []
        if DEFAULT_SYNTHETIC_EXPERIENCES_FILE.exists():
            with DEFAULT_SYNTHETIC_EXPERIENCES_FILE.open("r", encoding="utf-8") as handle:
                synthetic_data = json.load(handle)

        combined_data = data + synthetic_data
        return [Experience(**item) for item in combined_data]

    def save_experiences(self, experiences: List[Experience]) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        payload = [experience.model_dump(mode="json") for experience in experiences]
        with self.file_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=4)

    def add_experience(self, experience_data: Dict[str, Any]) -> Experience:
        experiences = self.load_experiences()
        experience_payload = dict(experience_data)
        if "state_delta" not in experience_payload:
            experience_payload["state_delta"] = build_experience_delta(
                experience_payload.get("state_before", {}),
                experience_payload.get("state_after", {}),
            )
        experience = Experience(**experience_payload)
        experiences.append(experience)
        self.save_experiences(experiences)
        return experience

    def get_experience(self, experience_id: str) -> Experience | None:
        experiences = self.load_experiences()
        for experience in experiences:
            if experience.experience_id == experience_id:
                return experience
        return None

    def get_all_experiences(self) -> List[Experience]:
        return self.load_experiences()


experience_service = ExperienceService()
