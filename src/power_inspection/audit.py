from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AuditLogger:
    def __init__(self, log_dir: Path, enabled: bool = True) -> None:
        self.enabled = enabled
        self.log_dir = log_dir
        self._lock = threading.Lock()
        self._log_file = self.log_dir / "api_events.jsonl"

    def log(self, event_type: str, payload: dict[str, Any]) -> None:
        if not self.enabled:
            return

        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            **payload,
        }
        self.log_dir.mkdir(parents=True, exist_ok=True)
        line = json.dumps(event, ensure_ascii=False)
        with self._lock:
            with self._log_file.open("a", encoding="utf-8") as handle:
                handle.write(line)
                handle.write("\n")
