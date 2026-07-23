from __future__ import annotations

import re
from collections import Counter
from typing import List


ACTION_FAMILIES = {
    "project": ["build", "develop", "create"],
    "learning": ["course", "study", "learn"],
    "competition": ["hackathon", "contest"],
    "experience": ["internship", "work"],
    "practice": ["dsa", "leetcode"],
}

ACTION_TOKEN_MAP = {
    "build python project": ["build", "python", "project"],
    "hackathon": ["competition", "project", "teamwork"],
    "internship": ["industry", "experience", "work"],
    "python course": ["python", "course", "learning"],
    "machine learning course": ["machine", "learning", "course"],
    "dsa course": ["dsa", "course", "algorithm"],
    "mock interview": ["interview", "practice", "communication"],
    "research paper": ["research", "paper", "reading"],
}


class ActionEncoder:
    def __init__(self) -> None:
        self.vocabulary = self._build_vocabulary()

    def _build_vocabulary(self) -> List[str]:
        tokens: List[str] = []
        for token_list in ACTION_TOKEN_MAP.values():
            for token in token_list:
                if token not in tokens:
                    tokens.append(token)
        for family_tokens in ACTION_FAMILIES.values():
            for token in family_tokens:
                if token not in tokens:
                    tokens.append(token)
        return tokens

    def tokenize(self, action: str) -> List[str]:
        lowered = action.strip().lower()
        raw_tokens = [token for token in re.findall(r"[a-z]+", lowered) if token]
        expanded_tokens: List[str] = []
        for token in raw_tokens:
            expanded_tokens.append(token)
            for family_name, family_tokens in ACTION_FAMILIES.items():
                if token in family_tokens:
                    expanded_tokens.append(family_name)
        return expanded_tokens

    def encode_action(self, action: str) -> List[float]:
        tokens = self.tokenize(action)
        vector = [0.0 for _ in self.vocabulary]
        counts = Counter(tokens)
        for index, vocab_token in enumerate(self.vocabulary):
            vector[index] = float(counts.get(vocab_token, 0.0))
        return vector

    def action_similarity(self, action_a: str, action_b: str) -> float:
        vector_a = self.encode_action(action_a)
        vector_b = self.encode_action(action_b)
        dot = sum(a * b for a, b in zip(vector_a, vector_b))
        norm_a = sum(value * value for value in vector_a) ** 0.5
        norm_b = sum(value * value for value in vector_b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


encoder = ActionEncoder()
