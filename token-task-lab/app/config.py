"""Provider and runtime configuration, read from the environment only.

Secrets never live in the repo: `LLM_API_KEY` is read here, forwarded to the
provider as an Authorization header, and never written into a run record.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNS_DIR = ROOT / "runs"

TRUTHY = {"1", "true", "yes", "on"}


def _env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


def _env_float(name: str, default: float) -> float:
    try:
        return float(_env(name) or default)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(_env(name) or default)
    except ValueError:
        return default


@dataclass(frozen=True)
class ProviderConfig:
    """OpenAI-compatible endpoint settings.

    `base_url` is expected to include the API version segment, e.g.
    ``https://api.openai.com/v1`` — the client appends ``/chat/completions``.
    """

    base_url: str = ""
    api_key: str = ""
    model: str = ""
    strong_model: str | None = None
    timeout_s: float = 60.0
    temperature: float = 0.2
    max_tokens: int = 900

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.api_key and self.model)

    @property
    def missing_settings(self) -> list[str]:
        missing = []
        if not self.base_url:
            missing.append("LLM_BASE_URL")
        if not self.api_key:
            missing.append("LLM_API_KEY")
        if not self.model:
            missing.append("LLM_MODEL")
        return missing

    def public(self) -> dict:
        """Config safe to hand to the browser — deliberately omits the key."""
        return {
            "base_url": self.base_url,
            "model": self.model,
            "strong_model": self.strong_model,
            "model_for_strong_steps": self.strong_model or self.model,
            "configured": self.configured,
            "missing_settings": self.missing_settings,
            "timeout_s": self.timeout_s,
        }


def load_provider_config() -> ProviderConfig:
    return ProviderConfig(
        base_url=_env("LLM_BASE_URL"),
        api_key=_env("LLM_API_KEY"),
        model=_env("LLM_MODEL"),
        strong_model=_env("LLM_STRONG_MODEL") or None,
        timeout_s=_env_float("LLM_TIMEOUT_S", 60.0),
        temperature=_env_float("LLM_TEMPERATURE", 0.2),
        max_tokens=_env_int("LLM_MAX_TOKENS", 900),
    )


def runs_dir() -> Path:
    return Path(_env("TOKEN_TASK_RUNS_DIR") or DEFAULT_RUNS_DIR)


def save_runs_enabled() -> bool:
    return _env("TOKEN_TASK_SAVE_RUNS", "1").lower() in TRUTHY
