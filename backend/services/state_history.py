from datetime import datetime
from typing import Dict, List


def build_state_history(entries: List[Dict]) -> List[Dict]:
    history = []
    for entry in entries:
        history.append(
            {
                "date": entry.get("date") or datetime.utcnow().date().isoformat(),
                "skills": entry.get("skills", {}),
            }
        )
    return history
