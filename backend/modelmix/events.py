"""ModelMix event schema v0 helpers."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class EventSequencer:
    """Assign a single monotonic sequence across multiplexed seat events."""

    run_id: str
    seq: int = 0

    def create(self, event_type: str, **payload: Any) -> Dict[str, Any]:
        self.seq += 1
        return {
            "run_id": self.run_id,
            "seq": self.seq,
            "type": event_type,
            "ts": time.time(),
            **payload,
        }
