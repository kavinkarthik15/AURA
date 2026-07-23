from datetime import datetime
from typing import Dict, List


class ExecutionTracker:
    def __init__(self) -> None:
        self.events: List[Dict] = []

    def record_event(self, action: str, status: str, step: int) -> Dict:
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "status": status,
            "step": step,
        }
        self.events.append(event)
        return event

    def get_events(self) -> List[Dict]:
        return list(self.events)
