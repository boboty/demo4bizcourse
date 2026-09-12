"""A minimal OpenAI-compatible chat client.

Deliberately built on httpx against the wire format rather than a vendor SDK, so
any endpoint that speaks ``POST {base_url}/chat/completions`` works and the
classroom can point it at whatever gateway the room has.

Every number this module returns comes from the provider's own response or from
a local ``perf_counter`` — nothing here is estimated.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Iterable

import httpx

from .config import ProviderConfig
from .models import TRUNCATING_FINISH_REASONS


class ProviderError(RuntimeError):
    """Raised when a completion cannot be obtained. Message is safe to display."""


@dataclass
class ProviderResult:
    text: str
    model: str
    input_tokens: int | None
    output_tokens: int | None
    cached_tokens: int | None
    latency_ms: int
    usage_raw: dict[str, Any] = field(default_factory=dict)
    # Why the completion stopped, as the provider reported it. ``None`` means
    # the gateway did not say — which is not the same as "stopped normally".
    finish_reason: str | None = None

    @property
    def truncated(self) -> bool:
        """True when the output cap ended the call, so `text` is a prefix."""
        return self.finish_reason in TRUNCATING_FINISH_REASONS


# Different OpenAI-compatible gateways spell cached-prompt accounting
# differently. Try the common ones, report None when none is present.
_CACHED_TOKEN_KEYS = (
    "cached_tokens",
    "cache_read_input_tokens",
    "prompt_cache_hit_tokens",
    "cache_hit_tokens",
)
_INPUT_TOKEN_KEYS = ("prompt_tokens", "input_tokens")
_OUTPUT_TOKEN_KEYS = ("completion_tokens", "output_tokens")


def _as_int(value: Any) -> int | None:
    # bool is an int subclass; a provider echoing `true` is not a token count.
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def _first_int(source: dict[str, Any], keys: Iterable[str]) -> int | None:
    for key in keys:
        found = _as_int(source.get(key))
        if found is not None:
            return found
    return None


def parse_usage(usage: Any) -> tuple[int | None, int | None, int | None]:
    """Return ``(input_tokens, output_tokens, cached_tokens)`` from a usage block.

    Any field the provider does not report stays ``None`` — the UI renders that
    as a dash rather than a zero, so a missing number is never mistaken for
    measured behaviour.
    """
    if not isinstance(usage, dict):
        return None, None, None

    input_tokens = _first_int(usage, _INPUT_TOKEN_KEYS)
    output_tokens = _first_int(usage, _OUTPUT_TOKEN_KEYS)

    cached_tokens = None
    details = usage.get("prompt_tokens_details")
    if isinstance(details, dict):
        cached_tokens = _first_int(details, _CACHED_TOKEN_KEYS)
    if cached_tokens is None:
        cached_tokens = _first_int(usage, _CACHED_TOKEN_KEYS)

    return input_tokens, output_tokens, cached_tokens


def parse_finish_reason(choice: Any) -> str | None:
    """How the provider says this completion ended, or ``None`` if it is silent.

    Only the value the provider actually sent is returned — a missing or blank
    ``finish_reason`` stays ``None``. Defaulting it to ``stop`` would turn "we
    were not told" into "it finished", which is the one thing this field exists
    to distinguish.
    """
    if not isinstance(choice, dict):
        return None
    value = choice.get("finish_reason")
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip().lower()


class OpenAICompatibleProvider:
    def __init__(self, config: ProviderConfig, client: httpx.Client | None = None):
        self.config = config
        # A client may be injected by tests; when absent each call opens its own
        # short-lived client so a classroom session never leaks a connection.
        self._client = client

    @property
    def configured(self) -> bool:
        return self.config.configured

    @property
    def model(self) -> str:
        return self.config.model

    def endpoint(self) -> str:
        return f"{self.config.base_url.rstrip('/')}/chat/completions"

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> ProviderResult:
        if not self.configured:
            raise ProviderError(
                "provider 未配置，缺少：" + "、".join(self.config.missing_settings)
            )

        payload = {
            "model": model or self.config.model,
            "messages": messages,
            "temperature": self.config.temperature if temperature is None else temperature,
            "max_tokens": self.config.max_tokens if max_tokens is None else max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        if self._client is not None:
            return self._post(self._client, payload, headers)
        with httpx.Client(timeout=self.config.timeout_s) as client:
            return self._post(client, payload, headers)

    def _post(self, client: httpx.Client, payload: dict, headers: dict) -> ProviderResult:
        started = time.perf_counter()
        try:
            response = client.post(self.endpoint(), headers=headers, json=payload)
        except httpx.HTTPError as exc:
            raise ProviderError(f"provider 请求失败：{exc}") from exc
        latency_ms = int((time.perf_counter() - started) * 1000)

        if response.status_code >= 400:
            raise ProviderError(
                f"provider 返回 HTTP {response.status_code}：{response.text[:300]}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise ProviderError(f"provider 返回的不是 JSON：{response.text[:200]}") from exc

        if isinstance(data, dict) and data.get("error"):
            raise ProviderError(f"provider 返回错误：{str(data['error'])[:300]}")

        choices = data.get("choices") if isinstance(data, dict) else None
        if not choices:
            raise ProviderError(f"provider 响应缺少 choices：{str(data)[:300]}")

        first = choices[0] or {}
        message = first.get("message") or {}
        if "content" in message:
            text = message.get("content") or ""
        elif "text" in first:
            text = first.get("text") or ""
        else:
            raise ProviderError(f"provider 响应缺少 message.content：{str(first)[:300]}")

        usage = data.get("usage")
        input_tokens, output_tokens, cached_tokens = parse_usage(usage)
        resolved_model = str(data.get("model") or payload["model"])

        return ProviderResult(
            text=text.strip(),
            model=resolved_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
            latency_ms=latency_ms,
            usage_raw=usage if isinstance(usage, dict) else {},
            finish_reason=parse_finish_reason(first),
        )
