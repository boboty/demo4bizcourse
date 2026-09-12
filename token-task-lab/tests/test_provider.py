"""Wire-level behaviour of the OpenAI-compatible client."""

from __future__ import annotations

import httpx
import pytest

from app.config import ProviderConfig
from app.provider import OpenAICompatibleProvider, ProviderError, parse_usage

CONFIG = ProviderConfig(
    base_url="https://example.invalid/v1",
    api_key="secret-key",
    model="test-model",
    timeout_s=5,
)


def provider_for(handler) -> OpenAICompatibleProvider:
    transport = httpx.MockTransport(handler)
    return OpenAICompatibleProvider(CONFIG, client=httpx.Client(transport=transport))


def reply(payload: dict, status_code: int = 200):
    return lambda request: httpx.Response(status_code, json=payload)


def text_reply(content: str = "好的", usage: dict | None = None):
    body = {"model": "test-model", "choices": [{"message": {"role": "assistant", "content": content}}]}
    if usage is not None:
        body["usage"] = usage
    return reply(body)


def test_completion_returns_text_and_usage():
    provider = provider_for(text_reply("交付内容", {"prompt_tokens": 120, "completion_tokens": 30}))
    result = provider.complete([{"role": "user", "content": "你好"}])

    assert result.text == "交付内容"
    assert result.model == "test-model"
    assert result.input_tokens == 120
    assert result.output_tokens == 30
    assert result.cached_tokens is None
    assert result.latency_ms >= 0


def test_endpoint_and_auth_header_are_what_the_wire_expects():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        return text_reply()(request)

    provider_for(handler).complete([{"role": "user", "content": "hi"}])

    assert seen["url"] == "https://example.invalid/v1/chat/completions"
    assert seen["auth"] == "Bearer secret-key"


def test_trailing_slash_in_base_url_does_not_double_up():
    config = ProviderConfig(base_url="https://example.invalid/v1/", api_key="k", model="m")
    provider = OpenAICompatibleProvider(config)
    assert provider.endpoint() == "https://example.invalid/v1/chat/completions"


def test_nested_prompt_tokens_details_are_read():
    provider = provider_for(
        text_reply("x", {"prompt_tokens": 100, "completion_tokens": 10,
                         "prompt_tokens_details": {"cached_tokens": 64}})
    )
    assert provider.complete([{"role": "user", "content": "hi"}]).cached_tokens == 64


@pytest.mark.parametrize(
    "usage, expected",
    [
        # DeepSeek-style cache accounting.
        ({"prompt_tokens": 100, "completion_tokens": 5, "prompt_cache_hit_tokens": 80},
         (100, 5, 80)),
        # Anthropic-style naming on a gateway that exposes it.
        ({"input_tokens": 90, "output_tokens": 4, "cache_read_input_tokens": 32},
         (90, 4, 32)),
        # No cache accounting at all: null, not zero.
        ({"prompt_tokens": 10, "completion_tokens": 2}, (10, 2, None)),
        ({}, (None, None, None)),
        (None, (None, None, None)),
    ],
)
def test_usage_dialects(usage, expected):
    assert parse_usage(usage) == expected


def test_http_error_is_surfaced_without_leaking_the_key():
    provider = provider_for(lambda request: httpx.Response(401, text="bad key"))
    with pytest.raises(ProviderError) as excinfo:
        provider.complete([{"role": "user", "content": "hi"}])

    message = str(excinfo.value)
    assert "401" in message
    assert "secret-key" not in message


def test_missing_choices_is_an_error_not_an_empty_answer():
    provider = provider_for(reply({"model": "test-model"}))
    with pytest.raises(ProviderError, match="choices"):
        provider.complete([{"role": "user", "content": "hi"}])


def test_error_body_is_reported():
    provider = provider_for(reply({"error": {"message": "quota exceeded"}}))
    with pytest.raises(ProviderError, match="quota exceeded"):
        provider.complete([{"role": "user", "content": "hi"}])


def test_non_json_body_is_reported():
    provider = provider_for(lambda request: httpx.Response(200, text="<html>gateway</html>"))
    with pytest.raises(ProviderError, match="JSON"):
        provider.complete([{"role": "user", "content": "hi"}])


def test_network_failure_is_wrapped():
    def handler(request):
        raise httpx.ConnectError("no route to host")

    provider = provider_for(handler)
    with pytest.raises(ProviderError, match="请求失败"):
        provider.complete([{"role": "user", "content": "hi"}])


def test_unconfigured_provider_refuses_rather_than_guessing():
    provider = OpenAICompatibleProvider(ProviderConfig())
    assert provider.configured is False
    with pytest.raises(ProviderError, match="LLM_BASE_URL"):
        provider.complete([{"role": "user", "content": "hi"}])


def test_public_config_never_exposes_the_key():
    public = CONFIG.public()
    assert "api_key" not in public
    assert "secret-key" not in str(public)


def test_model_override_reaches_the_request_body():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        seen.update(json.loads(request.content))
        return text_reply()(request)

    provider_for(handler).complete([{"role": "user", "content": "hi"}], model="strong-model")
    assert seen["model"] == "strong-model"
