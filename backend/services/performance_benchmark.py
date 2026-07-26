from __future__ import annotations

from contextlib import contextmanager
from time import perf_counter
from typing import Dict, Iterator


class PerformanceBenchmark:
    def __init__(self) -> None:
        self.timings_ms: Dict[str, float] = {}

    @contextmanager
    def measure(self, name: str) -> Iterator[None]:
        started = perf_counter()
        try:
            yield
        finally:
            self.timings_ms[name] = round((perf_counter() - started) * 1000, 4)

    def record(self, name: str, elapsed_ms: float) -> None:
        self.timings_ms[name] = round(elapsed_ms, 4)

    def to_dict(self) -> Dict[str, float]:
        return dict(self.timings_ms)
