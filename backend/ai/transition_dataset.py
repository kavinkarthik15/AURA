from typing import Dict, List


class TransitionDataset:
    def __init__(self, action_to_index: Dict[str, int] | None = None) -> None:
        self.action_to_index = action_to_index or {
            "Python Project": 1,
            "Complete Python Project": 1,
            "DSA Practice": 2,
            "Practice DSA": 2,
            "Complete DSA Course": 3,
            "DSA Course": 3,
            "Internship": 4,
            "Complete Internship": 4,
            "Hackathon": 5,
            "Participate in Hackathon": 5,
            "Course": 6,
            "Python Course": 6,
            "Machine Learning Course": 7,
            "Mock Interview": 8,
            "Attend Mock Interview": 8,
            "Research Paper": 9,
            "Read Research Paper": 9,
            "Research Paper Review": 9,
        }

    def encode_sample(self, state_before: Dict[str, int], action: str) -> List[int]:
        vector: List[int] = []
        for skill in sorted(state_before.keys()):
            vector.append(int(state_before[skill]))
        action_index = self.action_to_index.get(action, 0)
        vector.append(action_index)
        return vector

    def encode_dataset(self, dataset: List[Dict[str, int | str]]) -> List[List[int]]:
        return [self.encode_sample(sample["state_before"], sample["action"]) for sample in dataset]
