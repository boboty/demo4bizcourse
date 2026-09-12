"""Provider and runtime configuration for the classroom lab.

The classroom provider is intentionally fixed to DeepSeek. The only required
secret is ``LLM_API_KEY``; base URL and model are course assets, not classroom
setup knobs.

A local ``token-task-lab/.env`` is loaded automatically on import. Existing
shell environment variables win over values from the file.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNS_DIR = ROOT / "runs"

# Load the demo-local environment file automatically. ``override=False`` keeps
# an explicitly exported shell variable authoritative when both are present.
load_dotenv(ROOT / ".env", override=False)

# Classroom defaults. Keep these in one place so the runbook and health page can
# clearly show what will be called without asking the instructor to configure it.
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-flash"

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

    ``base_url`` and ``model`` default to the fixed DeepSeek classroom values.
    Tests and local experiments may still construct this dataclass with explicit
    values, but ``load_provider_config`` deliberately does not read env overrides
    for them.
    """

    base_url: str = DEEPSEEK_BASE_URL
    api_key: str = ""
    model: str = DEEPSEEK_MODEL
    strong_model: str | None = None
    timeout_s: float = 60.0
    temperature: float = 0.2
    max_tokens: int = 900

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.api_key and self.model)

    @property
    def missing_settings(self) -> list[str]:
        # Base URL and model are fixed by the course. The instructor only needs
        # to provide the DeepSeek API key.
        return [] if self.api_key else ["LLM_API_KEY"]

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
        base_url=DEEPSEEK_BASE_URL,
        api_key=_env("LLM_API_KEY"),
        model=DEEPSEEK_MODEL,
        strong_model=_env("LLM_STRONG_MODEL") or None,
        timeout_s=_env_float("LLM_TIMEOUT_S", 60.0),
        temperature=_env_float("LLM_TEMPERATURE", 0.2),
        max_tokens=_env_int("LLM_MAX_TOKENS", 900),
    )


def runs_dir() -> Path:
    return Path(_env("TOKEN_TASK_RUNS_DIR") or DEFAULT_RUNS_DIR)


def save_runs_enabled() -> bool:
    return _env("TOKEN_TASK_SAVE_RUNS", "1").lower() in TRUTHY
