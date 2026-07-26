from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any, Dict, Iterable, List, Sequence, Set


class ExperienceEmbedder:
    def __init__(self) -> None:
        self.vocabulary: Set[str] = set()

    def fit(self, records: Iterable[Dict[str, Any]]) -> None:
        self.vocabulary = set()
        for record in records:
            self.vocabulary.update(self._tokens_for_record(record))

    def transform(self, record: Dict[str, Any]) -> Dict[str, float]:
        tokens = self._tokens_for_record(record)
        if not tokens:
            return {}
        counts = Counter(tokens)
        if not self.vocabulary:
            return {token: float(count) for token, count in counts.items()}
        return {token: float(counts.get(token, 0.0)) for token in sorted(self.vocabulary)}

    def similarity(self, left: Dict[str, Any], right: Dict[str, Any]) -> float:
        left_vector = self.transform(left)
        right_vector = self.transform(right)
        if not left_vector and not right_vector:
            return 1.0
        if not left_vector or not right_vector:
            return 0.0
        keys = set(left_vector) | set(right_vector)
        dot = sum(left_vector.get(key, 0.0) * right_vector.get(key, 0.0) for key in keys)
        left_norm = math.sqrt(sum(value * value for value in left_vector.values()))
        right_norm = math.sqrt(sum(value * value for value in right_vector.values()))
        if left_norm == 0 or right_norm == 0:
            return 1.0 if left_vector == right_vector else 0.0
        return round(dot / (left_norm * right_norm), 4)

    def _tokens_for_record(self, record: Dict[str, Any]) -> List[str]:
        text_parts: List[str] = []
        goal = record.get("goal_name") or record.get("goal") or ""
        text_parts.append(str(goal))
        actions = record.get("actions") or []
        if isinstance(actions, Sequence) and not isinstance(actions, (str, bytes)):
            text_parts.extend([str(action) for action in actions])
        completed = record.get("completed_actions") or []
        if isinstance(completed, Sequence) and not isinstance(completed, (str, bytes)):
            text_parts.extend([str(action) for action in completed])
        state = record.get("initial_state") or record.get("state") or {}
        if isinstance(state, dict):
            for key, value in state.items():
                text_parts.append(str(key))
                if value not in (None, ""):
                    text_parts.append(str(value))
        return self._tokenize(" ".join(text_parts))

    def _tokenize(self, text: str) -> List[str]:
        return [token for token in re.findall(r"[a-z0-9]+", text.lower()) if token]
