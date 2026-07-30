from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def load_dotenv(path: Path | str = ".env", *, override: bool = True) -> None:
    """Load a small, dependency-free subset of dotenv syntax.

    An explicitly selected project ``.env`` is authoritative by default. This
    prevents a stale parent-shell value from silently overriding a key that the
    user just updated in the project.
    """
    env_path = Path(path)
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value and value[0] in {"'", '"'} and value[-1:] == value[0]:
            value = value[1:-1]
        if override or key not in os.environ:
            os.environ[key] = value


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    api_key: str
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-v4-flash"
    data_dir: Path = Path(".agent_data")
    max_steps: int = 8
    context_max_messages: int = 24
    context_max_chars: int = 24_000
    request_timeout: int = 60
    trace_reasoning: bool = False

    @classmethod
    def from_env(cls, dotenv_path: Path | str = ".env") -> "Settings":
        load_dotenv(dotenv_path, override=True)
        return cls(
            api_key=os.getenv("DEEPSEEK_API_KEY", "").strip(),
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/"),
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
            data_dir=Path(os.getenv("AGENT_DATA_DIR", ".agent_data")),
            max_steps=int(os.getenv("AGENT_MAX_STEPS", "8")),
            context_max_messages=int(os.getenv("AGENT_CONTEXT_MAX_MESSAGES", "24")),
            context_max_chars=int(os.getenv("AGENT_CONTEXT_MAX_CHARS", "24000")),
            request_timeout=int(os.getenv("AGENT_REQUEST_TIMEOUT", "60")),
            trace_reasoning=_as_bool(os.getenv("AGENT_TRACE_REASONING", "false")),
        )

    def require_api_key(self) -> None:
        if not self.api_key:
            raise ValueError(
                "未配置 DEEPSEEK_API_KEY。请复制 .env.example 为 .env 并填写 API Key。"
            )
