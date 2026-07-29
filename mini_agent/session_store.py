from __future__ import annotations

import json
import re
import threading
from dataclasses import asdict
from pathlib import Path

from .tracing import utc_now
from .types import Session


_SAFE_SESSION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


class SessionStore:
    """Durable JSON session storage with atomic replacement."""

    def __init__(self, root: Path):
        self.root = root
        self._lock = threading.RLock()

    def _path(self, session_id: str) -> Path:
        if not _SAFE_SESSION_ID.fullmatch(session_id):
            raise ValueError("session_id 只能包含字母、数字、点、下划线和连字符")
        return self.root / "sessions" / f"{session_id}.json"

    def load(self, session_id: str) -> Session:
        path = self._path(session_id)
        with self._lock:
            if not path.exists():
                now = utc_now()
                return Session(session_id=session_id, created_at=now, updated_at=now)
            data = json.loads(path.read_text(encoding="utf-8"))
            return Session(
                session_id=data["session_id"],
                messages=data.get("messages", []),
                summary=data.get("summary", ""),
                state=data.get("state", {}),
                created_at=data.get("created_at", ""),
                updated_at=data.get("updated_at", ""),
            )

    def save(self, session: Session) -> None:
        path = self._path(session.session_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        session.updated_at = utc_now()
        temp_path = path.with_suffix(".json.tmp")
        content = json.dumps(asdict(session), ensure_ascii=False, indent=2)
        with self._lock:
            temp_path.write_text(content, encoding="utf-8")
            temp_path.replace(path)

    def list_sessions(self) -> list[dict[str, str]]:
        folder = self.root / "sessions"
        if not folder.exists():
            return []
        result = []
        for path in sorted(folder.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                result.append(
                    {
                        "session_id": str(data.get("session_id", path.stem)),
                        "updated_at": str(data.get("updated_at", "")),
                        "message_count": str(len(data.get("messages", []))),
                    }
                )
            except (OSError, json.JSONDecodeError):
                continue
        return sorted(result, key=lambda item: item["updated_at"], reverse=True)
