from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import ProviderConfig  # noqa: E402
from app.provider import ProviderError, ProviderResult  # noqa: E402

LLM_ENV_VARS = (
    "LLM_BASE_URL",
    "LLM_API_KEY",
    "LLM_MODEL",
    "LLM_STRONG_MODEL",
    "LLM_TIMEOUT_S",
    "LLM_TEMPERATURE",
    "LLM_MAX_TOKENS",
)


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch, tmp_path):
    """No ambient provider credentials, and never write into the repo's runs/."""
    for name in LLM_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("TOKEN_TASK_RUNS_DIR", str(tmp_path / "runs"))
    return tmp_path


class FakeProvider:
    """A provider that reports honest, prompt-size-driven numbers.

    `input_tokens` is derived from the prompt it was actually handed, so a mode
    that really sends more context really reports more input tokens. That is
    what lets the D-vs-C test assert something meaningful instead of comparing
    two hand-written constants.
    """

    def __init__(self, model: str = "fake-base", cached_tokens: int | None = None,
                 fail_on_call: int | None = None):
        self.model = model
        self.configured = True
        self.cached_tokens = cached_tokens
        self.fail_on_call = fail_on_call
        self.requests: list[dict] = []

    @property
    def call_count(self) -> int:
        return len(self.requests)

    def complete(self, messages, *, model=None, temperature=None, max_tokens=None) -> ProviderResult:
        self.requests.append({"messages": messages, "model": model})
        index = len(self.requests)
        if self.fail_on_call == index:
            raise ProviderError("fake provider failure")

        prompt_chars = sum(len(m["content"]) for m in messages)
        prompt_tokens = prompt_chars // 4
        return ProviderResult(
            # Identifiable per call, so a test can prove which step's output
            # ended up where on the Demo 1 page.
            text=f"回答{index}",
            model=model or self.model,
            input_tokens=prompt_tokens,
            output_tokens=20,
            cached_tokens=self.cached_tokens,
            latency_ms=7,
            usage_raw={"prompt_tokens": prompt_tokens, "completion_tokens": 20},
        )


@pytest.fixture
def provider_config() -> ProviderConfig:
    return ProviderConfig(
        base_url="https://example.invalid/v1",
        api_key="test-key",
        model="fake-base",
    )
