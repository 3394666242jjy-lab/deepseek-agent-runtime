from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TraceLogger:
    """Append-only JSONL execution trace, one file per session."""

    def __init__(self, trace_dir: Path, include_reasoning: bool = False):
        self.trace_dir = trace_dir
        self.include_reasoning = include_reasoning
        self._lock = threading.Lock()

    def emit(self, session_id: str, event: str, **payload: Any) -> dict[str, Any]:
        if not self.include_reasoning:
            payload.pop("reasoning", None)
        record = {"time": utc_now(), "session_id": session_id, "event": event, **payload}
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        path = self.trace_dir / f"{session_id}.jsonl"
        line = json.dumps(record, ensure_ascii=False, default=str)
        with self._lock:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        return record

    def read(self, session_id: str, limit: int = 50) -> list[dict[str, Any]]:
        path = self.trace_dir / f"{session_id}.jsonl"
        if not path.exists():
            return []
        lines = path.read_text(encoding="utf-8").splitlines()[-limit:]
        return [json.loads(line) for line in lines if line.strip()]
