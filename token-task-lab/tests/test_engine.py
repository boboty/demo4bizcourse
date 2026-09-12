"""The four modes, asserted on structure and on recorded usage."""

from __future__ import annotations

import pytest

from app.config import ProviderConfig
from app.engine import MODES, RunEngine
from app.provider import ProviderResult
from app.scenarios import get_scenario
from tests.conftest import FakeProvider

SCENARIO = get_scenario("tianjin-freight")


def engine(provider: FakeProvider, config: ProviderConfig) -> RunEngine:
    return RunEngine(provider=provider, config=config)


def run(provider: FakeProvider, config: ProviderConfig, mode: str):
    return engine(provider, config).execute(
        scenario=SCENARIO, mode=mode, request_text=SCENARIO.request_text
    )


def test_every_mode_is_priceable():
    assert set(MODES) == {"A", "B", "C", "D"}


def test_structure_only_records_carry_no_numbers(provider_config):
    """Without a provider the chain shape is shown and nothing is invented."""
    from app.config import ProviderConfig as Cfg
    from app.engine import RunEngine as Engine
    from app.provider import OpenAICompatibleProvider

    unconfigured = Engine(OpenAICompatibleProvider(Cfg()), Cfg())
    for mode in MODES:
        record = unconfigured.execute(
            scenario=SCENARIO, mode=mode, request_text=SCENARIO.request_text
        )
        assert record.evidence_level == "structure_only"
        assert record.usage.model_calls == 0
        assert record.usage.input_tokens is None
        assert record.usage.output_tokens is None
        assert record.usage.cached_tokens is None
        assert record.usage.total_tokens is None
        assert all(step.input_tokens is None for step in record.steps)
        assert all(step.model is None for step in record.steps)


# ---------------------------------------------------------------- A


def test_mode_a_makes_exactly_one_call_and_no_tool_calls(provider_config):
    provider = FakeProvider()
    record = run(provider, provider_config, "A")

    assert provider.call_count == 1
    assert record.usage.model_calls == 1
    assert record.usage.tool_calls == 0
    assert [step.phase for step in record.steps] == ["direct"]

    # The customer's raw words, and nothing else — no material, no tool result.
    sent = provider.requests[0]["messages"]
    assert sent[-1]["content"] == SCENARIO.request_text
    prompt = "".join(m["content"] for m in sent)
    assert all(material.title not in prompt for material in SCENARIO.materials)


# ---------------------------------------------------------------- B


def test_mode_b_sends_everything_in_one_call(provider_config):
    provider = FakeProvider()
    record = run(provider, provider_config, "B")

    assert provider.call_count == 1
    assert record.usage.tool_calls == len(SCENARIO.tools)
    assert [step.phase for step in record.steps] == ["context", "answer"]

    prompt = provider.requests[0]["messages"][-1]["content"]
    for material in SCENARIO.materials:
        assert material.title in prompt
    assert "provenance=teaching_fixture" in prompt


# ---------------------------------------------------------------- C


def test_mode_c_follows_the_declared_chain(provider_config):
    provider = FakeProvider()
    record = run(provider, provider_config, "C")

    assert [step.phase for step in record.steps] == [
        "parse",
        "gaps",
        "facts",
        "judge",
        "verify",
        "deliver",
    ]
    # One task, six steps — but only five of them are model calls.
    assert len(record.steps) == 6
    assert record.usage.model_calls == 5
    assert record.usage.tool_calls == len(SCENARIO.fact_tools)
    assert provider.call_count == 5


def test_mode_c_stops_at_the_human_gate_when_facts_are_missing(provider_config):
    record = run(FakeProvider(), provider_config, "C")

    facts_step = next(step for step in record.steps if step.phase == "facts")
    deliver_step = next(step for step in record.steps if step.phase == "deliver")

    # The rate card and the capacity check genuinely have nothing to return.
    assert facts_step.status == "blocked"
    assert "查询运价" in facts_step.detail
    assert deliver_step.status == "waiting_human"
    assert record.run_status == "waiting_human"


# ---------------------------------------------------------------- D


def test_mode_d_costs_measurably_more_than_c_for_the_same_goal(provider_config):
    """The whole demonstration: same task, real repeated work, bigger numbers."""
    c_record = run(FakeProvider(), provider_config, "C")
    d_record = run(FakeProvider(), provider_config, "D")

    assert d_record.request_text == c_record.request_text
    assert d_record.mode != c_record.mode

    assert d_record.usage.model_calls > c_record.usage.model_calls
    assert d_record.usage.tool_calls > c_record.usage.tool_calls
    assert d_record.usage.input_tokens > c_record.usage.input_tokens
    assert d_record.usage.total_tokens > c_record.usage.total_tokens

    # And the extra input is attributable to the repeated context, not to a
    # longer question: the repeated step really does carry a bigger prompt.
    c_judge = next(s for s in c_record.steps if s.phase == "judge")
    d_judge = next(s for s in d_record.steps if s.phase == "d-judge-dup")
    assert d_judge.input_tokens > c_judge.input_tokens


def test_mode_d_uses_the_strong_model_when_one_is_configured(provider_config):
    strong_config = ProviderConfig(
        base_url=provider_config.base_url,
        api_key=provider_config.api_key,
        model="fake-base",
        strong_model="fake-strong",
    )
    provider = FakeProvider()
    record = run(provider, strong_config, "D")

    strong_step = next(s for s in record.steps if s.phase == "d-judge-strong")
    assert strong_step.model == "fake-strong"
    # Call order in D: parse, parse, judge-strong, judge-dup, verify, verify, deliver.
    assert provider.requests[2]["model"] == "fake-strong"


def test_mode_d_says_so_when_no_strong_model_is_configured(provider_config):
    record = run(FakeProvider(), provider_config, "D")

    strong_step = next(s for s in record.steps if s.phase == "d-judge-strong")
    assert strong_step.model == "fake-base"
    assert any("LLM_STRONG_MODEL" in note for note in record.notes)


# ---------------------------------------------------------------- usage


def test_cached_tokens_stay_null_when_the_provider_reports_none(provider_config):
    record = run(FakeProvider(cached_tokens=None), provider_config, "C")

    assert record.usage.cached_tokens is None
    assert all(step.cached_tokens is None for step in record.steps)


def test_cached_tokens_are_summed_when_the_provider_reports_them(provider_config):
    record = run(FakeProvider(cached_tokens=64), provider_config, "C")

    assert record.usage.cached_tokens == 64 * record.usage.model_calls


def test_totals_come_from_the_steps(provider_config):
    record = run(FakeProvider(), provider_config, "C")

    model_steps = [s for s in record.steps if s.model]
    assert len(model_steps) == record.usage.model_calls
    assert record.usage.input_tokens == sum(s.input_tokens for s in model_steps)
    assert record.usage.output_tokens == sum(s.output_tokens for s in model_steps)
    assert record.usage.total_tokens == (
        record.usage.input_tokens + record.usage.output_tokens
    )
    assert record.usage.latency_ms == sum(s.latency_ms or 0 for s in record.steps)


def test_tool_only_steps_are_not_counted_as_model_calls(provider_config):
    record = run(FakeProvider(), provider_config, "C")

    for step in record.steps:
        if step.tool_calls:
            assert step.model is None
            assert step.input_tokens is None


# ---------------------------------------------------------------- failure


def test_a_failed_call_is_recorded_without_inventing_numbers(provider_config):
    provider = FakeProvider(fail_on_call=3)
    record = run(provider, provider_config, "C")

    assert record.run_status == "error"
    assert record.evidence_level == "live"
    assert "fake provider failure" in record.error

    failed = record.steps[-1]
    assert failed.status == "error"
    assert failed.model is None
    assert failed.input_tokens is None

    # parse, gaps, facts (tools only), then the failed judge call.
    assert [step.phase for step in record.steps] == ["parse", "gaps", "facts", "judge"]
    # The two calls that did succeed still carry their real numbers.
    assert record.usage.model_calls == 2
    assert record.usage.tool_calls == len(SCENARIO.fact_tools)
    assert record.usage.input_tokens > 0


def test_unknown_mode_is_a_key_error_not_a_silent_default(provider_config):
    with pytest.raises(KeyError):
        run(FakeProvider(), provider_config, "Z")


# ------------------------------------------- C 交付不得丢失客户已经给出的条件
#
# 「没有可核验来源就写待业务资料」这条规则只适用于外部业务事实。客户自己说过的
# 起运港、目的港、箱型箱量是任务输入，校验与交付都不得把它们改写成待确认；一旦
# 交付步骤只拿到校验稿，这些条件就会随校验的改写一起消失。下面几条钉住这一点。


def test_deliver_gets_the_raw_request_the_parse_and_the_check(provider_config):
    """最终交付必须同时拿到客户原话、已解析需求、已校验结果三者。"""
    provider = FakeProvider()
    run(provider, provider_config, "C")

    # C 档调用顺序：parse=1, gaps=2, judge=3, verify=4, deliver=5。
    deliver_prompt = provider.requests[4]["messages"][-1]["content"]
    assert SCENARIO.request_text in deliver_prompt  # 客户原话
    assert "回答1" in deliver_prompt  # 已解析需求 parsed
    assert "回答4" in deliver_prompt  # 已校验结果 checked


def test_deliver_keeps_every_condition_the_customer_already_stated(provider_config):
    provider = FakeProvider()
    run(provider, provider_config, "C")

    deliver_prompt = provider.requests[4]["messages"][-1]["content"]
    for condition in ("天津新港", "釜山", "20GP", "下周三"):
        assert condition in deliver_prompt
    # 「下周三」按客户口径保留；只有落到具体日期时才提示待确认。
    assert "具体日期待确认" in deliver_prompt


def test_deliver_separates_customer_inputs_from_external_business_facts(provider_config):
    provider = FakeProvider()
    run(provider, provider_config, "C")
    deliver_prompt = provider.requests[4]["messages"][-1]["content"]

    assert "客户明确陈述的任务输入" in deliver_prompt
    assert "外部业务事实" in deliver_prompt
    # 客户输入不要求来源核验，且不得被改写；外部事实没有来源就只能待业务资料。
    assert "不得改写成「待确认」" in deliver_prompt
    assert "待业务资料" in deliver_prompt


def test_the_check_step_is_also_told_not_to_strip_customer_inputs(provider_config):
    """校验步骤是改写发生的地方，它同样要知道客户陈述的条件不属于改写范围。"""
    provider = FakeProvider()
    run(provider, provider_config, "C")

    verify_prompt = provider.requests[3]["messages"][-1]["content"]
    assert "客户明确陈述的任务输入" in verify_prompt
    assert "必须原样保留" in verify_prompt


class LosingVerifyProvider(FakeProvider):
    """一个把客户已知条件也改写成「待确认」的校验步骤。

    最坏情况被真实地造出来：交付步骤如果只继承校验稿，客户的港口与箱量就会丢。
    """

    def complete(self, messages, *, model=None, temperature=None, max_tokens=None):
        if "待校验草稿" not in messages[-1]["content"]:
            return super().complete(messages, model=model)
        self.requests.append({"messages": messages, "model": model})
        prompt_tokens = sum(len(m["content"]) for m in messages) // 4
        return ProviderResult(
            text="起运港：待确认；目的港：待确认；箱型箱量：待确认；运价：待业务资料。",
            model=model or self.model,
            input_tokens=prompt_tokens,
            output_tokens=20,
            cached_tokens=None,
            latency_ms=7,
            usage_raw={"prompt_tokens": prompt_tokens, "completion_tokens": 20},
            finish_reason="stop",
        )


def test_deliver_still_has_the_customer_inputs_after_the_check_step_lost_them(
    provider_config,
):
    provider = LosingVerifyProvider()
    record = run(provider, provider_config, "C")

    assert record.run_status == "waiting_human"
    deliver_prompt = provider.requests[-1]["messages"][-1]["content"]
    # 上游确实把客户条件抹掉了……
    assert "起运港：待确认" in deliver_prompt
    # ……但交付步骤手里还有客户原话，所以这些条件没有跟着丢。
    for condition in ("天津新港", "釜山", "20GP", "下周三"):
        assert condition in deliver_prompt


def test_mode_d_deliver_carries_the_same_customer_inputs_as_c(provider_config):
    """D 档业务目标与 C 档相同，交付口径不能因为「低效版」就变窄。"""
    provider = FakeProvider()
    run(provider, provider_config, "D")

    # D 档调用顺序：parse ×2、judge-strong、judge-dup、verify ×2、deliver。
    deliver_prompt = provider.requests[-1]["messages"][-1]["content"]
    assert SCENARIO.request_text in deliver_prompt  # 客户原话
    assert "回答1" in deliver_prompt  # 已解析需求
    assert "回答6" in deliver_prompt  # 第二次校验的结果 = 已校验内容
    for condition in ("天津新港", "釜山", "20GP", "下周三"):
        assert condition in deliver_prompt


# ---------------------------------------------------------------- claim audit


def test_claim_audit_flags_concrete_commitments():
    from app.engine import audit_claims

    clean = audit_claims("运价待业务资料，舱位需人工确认。")
    assert clean.verdict == "no_concrete_commitment_detected"

    flagged = audit_claims("20GP 报价 USD 1200，下周三五截关，船名 FAKE-0001E。")
    assert flagged.verdict == "contains_concrete_commitments"
    assert flagged.price_mentions
    assert flagged.schedule_mentions
    assert "不是事实核验" in flagged.disclaimer
