"""The A/B/C/D experiment engine.

Four ways of attacking one business task. What separates them is not wording but
structure, and every difference the class sees is produced by a real call:

* A 直接回答     — one model call, customer's raw words only.
* B 全量上下文   — one model call, every available material pasted in at once.
* C 任务链       — 解析 → 判断缺口 → 获取事实 → 判断 → 校验 → 输出.
* D 低效版本     — same goal, deliberately repeated context and repeated steps
                   (plus an optional stronger model), all really executed.

No runner may write a token number itself. Numbers arrive from `ProviderResult`,
which got them from the provider's own `usage` block.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from uuid import uuid4

from .config import ProviderConfig
from .models import (
    ClaimAudit,
    RunRecord,
    StepRecord,
    UsageSummary,
    utc_now_iso,
)
from .provider import OpenAICompatibleProvider, ProviderError
from .scenarios.base import Scenario
from .tools import ToolBox, ToolCall

MODE_LABELS: dict[str, str] = {
    "A": "A 直接回答",
    "B": "B 全量上下文",
    "C": "C 任务链",
    "D": "D 低效版本",
}
MODES: tuple[str, ...] = tuple(MODE_LABELS)

# How many times the low-efficiency mode re-pastes the same context. Real
# repeated input, billed as repeated input — this is the whole demonstration.
D_CONTEXT_REPEAT = 3


class StepFailure(RuntimeError):
    """A model call failed; the record keeps every step that succeeded."""

    def __init__(self, message: str, step: StepRecord):
        super().__init__(message)
        self.step = step


# --------------------------------------------------------------------------
# claim audit — a locator, not a fact check
# --------------------------------------------------------------------------

_PRICE_PATTERN = re.compile(
    r"(?:USD|CNY|RMB|JPY|EUR|HKD)\s?\d[\d,]*(?:\.\d+)?"
    r"|\$\s?\d[\d,]*(?:\.\d+)?"
    r"|\d[\d,]*(?:\.\d+)?\s?(?:美元|美金|元|块)",
    re.IGNORECASE,
)
_SCHEDULE_PATTERN = re.compile(
    r"\d{4}\s?[-/年]\s?\d{1,2}\s?[-/月]\s?\d{1,2}\s?日?"
    r"|\d{1,2}\s?月\s?\d{1,2}\s?日"
    r"|周[一二三四五六日天]"
    r"|ETD|ETA|开船|截关|截港|航次|船名|VGM",
    re.IGNORECASE,
)

_AUDIT_LIMIT = 8


def audit_claims(text: str | None) -> ClaimAudit:
    """Flag sentences that look like concrete commitments.

    This is a keyword scan over the produced text. It cannot tell a sourced
    number from an invented one, and it is labelled as such wherever it is
    shown — it exists so the instructor can find the sentence to point at.
    """
    if not text:
        return ClaimAudit(verdict="no_output")

    prices = [m.group(0).strip() for m in _PRICE_PATTERN.finditer(text)][:_AUDIT_LIMIT]
    schedules = [m.group(0).strip() for m in _SCHEDULE_PATTERN.finditer(text)][:_AUDIT_LIMIT]
    verdict = (
        "contains_concrete_commitments"
        if prices or schedules
        else "no_concrete_commitment_detected"
    )
    return ClaimAudit(
        price_mentions=prices,
        schedule_mentions=schedules,
        verdict=verdict,
    )


# --------------------------------------------------------------------------
# context handed between chain steps
# --------------------------------------------------------------------------


@dataclass
class RunContext:
    scenario: Scenario
    mode: str
    request_text: str
    provider: OpenAICompatibleProvider
    config: ProviderConfig
    toolbox: ToolBox
    steps: list[StepRecord] = field(default_factory=list)
    texts: dict[str, str] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    @property
    def system_prompt(self) -> str:
        rules = self.scenario.rules_block()
        parts = [self.scenario.persona, f"业务目标：{self.scenario.task}"]
        if rules:
            parts.append("硬性要求：\n" + rules)
        return "\n\n".join(parts)

    def _next_index(self) -> int:
        return len(self.steps) + 1

    def ask(
        self,
        *,
        phase: str,
        action: str,
        user: str,
        system: str | None = None,
        model: str | None = None,
        status: str = "ok",
        detail: str | None = None,
    ) -> str:
        """Make one real model call and record everything it reports back."""
        messages = [
            {"role": "system", "content": system or self.system_prompt},
            {"role": "user", "content": user},
        ]
        resolved_model = model or self.provider.model
        started = time.perf_counter()
        try:
            result = self.provider.complete(messages, model=model)
        except ProviderError as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            failure_step = StepRecord(
                step=self._next_index(),
                action=action,
                phase=phase,
                status="error",
                model=None,
                latency_ms=latency_ms,
                detail=f"{resolved_model}: {exc}",
            )
            self.steps.append(failure_step)
            raise StepFailure(str(exc), failure_step) from exc

        self.steps.append(
            StepRecord(
                step=self._next_index(),
                action=action,
                phase=phase,
                status=status,
                model=result.model,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                cached_tokens=result.cached_tokens,
                tool_calls=0,
                latency_ms=result.latency_ms,
                result=result.text or None,
                detail=detail,
                usage_raw=result.usage_raw or None,
            )
        )
        self.texts[phase] = result.text
        return result.text

    def call_tools(self, names, *, phase: str, action: str) -> list[ToolCall]:
        """Invoke tools and record the batch as one step with no model call."""
        calls = self.toolbox.call_many(list(names))
        self.steps.append(
            StepRecord(
                step=self._next_index(),
                action=action,
                phase=phase,
                status="ok",
                tool_calls=len(calls),
                tools=[call.name for call in calls],
                latency_ms=0,
                detail="、".join(f"{call.title}={'有结果' if call.available else '无结果'}" for call in calls),
            )
        )
        return calls

    def patch_last_step(self, **fields) -> None:
        step = self.steps[-1]
        for key, value in fields.items():
            setattr(step, key, value)


# --------------------------------------------------------------------------
# mode runners
# --------------------------------------------------------------------------


def _fact_block(ctx: RunContext, calls: list[ToolCall]) -> str:
    return ctx.toolbox.render(calls)


def run_mode_a(ctx: RunContext) -> tuple[str, str]:
    """A 直接回答 — customer's raw words, nothing else, asked for a deliverable."""
    output = ctx.ask(
        phase="direct",
        action="直接回答客户问题",
        user=ctx.request_text,
        system=(
            f"{ctx.scenario.persona}\n\n"
            "请直接给出客户可交付的结果。不要描述你的推理过程，不要向客户反问。"
        ),
    )
    ctx.notes.append("A 档只把客户原话交给模型：没有业务资料、没有工具调用。模型若编造船期或运价，本档会留下证据；模型若谨慎停下，同样成立。")
    return output, "ok"


def run_mode_b(ctx: RunContext) -> tuple[str, str]:
    """B 全量上下文 — one call with every available material stuffed in."""
    calls = ctx.call_tools(
        [tool.name for tool in ctx.scenario.tools],
        phase="context",
        action="装载当前可用业务资料",
    )
    context = f"{ctx.scenario.materials_block()}\n\n{_fact_block(ctx, calls)}"
    output = ctx.ask(
        phase="answer",
        action="基于全量上下文生成可交付结果",
        user=(
            f"客户原话：\n{ctx.request_text}\n\n"
            f"当前可用业务资料与工具结果：\n{context}\n\n"
            "请基于以上全部资料，形成可交付结果。"
        ),
    )
    ctx.notes.append("B 档一次性把当前可用资料全部塞进上下文：任务是同一件，输入量随资料量线性增长。")
    return output, "ok"


def run_mode_c(ctx: RunContext) -> tuple[str, str]:
    """C 任务链 — the main version, six steps, facts fetched mid-chain."""
    scenario = ctx.scenario

    parsed = ctx.ask(
        phase="parse",
        action="解析客户需求",
        user=(
            f"客户原话：\n{ctx.request_text}\n\n"
            "请解析为结构化需求：起运港、目的港、箱型箱量、货好时间、客户期望。只输出结论。"
        ),
    )

    gaps = ctx.ask(
        phase="gaps",
        action="判断缺口",
        user=(
            f"需求解析：\n{parsed}\n\n"
            f"当前可用资料清单：\n{scenario.materials_block()}\n\n"
            "要完成这件任务，还缺哪些只能由外部事实或人工确认补上的条件？只列缺口，不要编造内容。"
        ),
    )

    fact_calls = ctx.call_tools(
        scenario.fact_tools, phase="facts", action="获取可核验业务事实"
    )
    missing = ctx.toolbox.missing_facts()
    if missing:
        ctx.patch_last_step(
            status="blocked",
            detail="未取回：" + "、".join(spec.title for spec in missing),
        )
    else:
        ctx.patch_last_step(detail="全部事实来源已取回")
    fact_block = _fact_block(ctx, fact_calls)

    judgment = ctx.ask(
        phase="judge",
        action="业务判断与人工确认点",
        user=(
            f"需求解析：\n{parsed}\n\n"
            f"已识别缺口：\n{gaps}\n\n"
            f"已取回事实（注意每条的 provenance 与 verified 标记）：\n{fact_block}\n\n"
            "请给出候选方案与必须停下来的人工确认点。没有可核验来源的数字一律写「待业务资料」。"
        ),
    )

    checked = ctx.ask(
        phase="verify",
        action="校验：不得把未核验资料写成事实",
        user=(
            f"待校验草稿：\n{judgment}\n\n"
            f"事实依据：\n{fact_block}\n\n"
            "逐条检查草稿：凡是没有可核验来源的船期、运价、舱位承诺，一律改为「待业务资料 / 人工确认」。"
            "然后输出修订后的草稿。"
        ),
    )

    output = ctx.ask(
        phase="deliver",
        action="形成可交付结果与停止点",
        status="waiting_human",
        user=(
            f"已校验内容：\n{checked}\n\n"
            "请输出最终可交付结果：先给结论，再给缺失条件与下一步动作，最后列出人工确认点。"
        ),
    )
    ctx.notes.append(
        "C 档按「解析 → 判断缺口 → 获取事实 → 判断 → 校验 → 输出」执行；"
        "事实取回步骤中有工具返回「无结果」时，该步标记 blocked，任务停在人工确认点。"
    )
    return output, "waiting_human"


def run_mode_d(ctx: RunContext) -> tuple[str, str]:
    """D 低效版本 — same goal, genuinely repeated work.

    Every repetition below is a real call against the real provider. Nothing in
    this function alters a recorded number; it only sends more of them.
    """
    scenario = ctx.scenario

    # 同一批资料取两次，两次都真的调用。
    first = ctx.call_tools(
        scenario.fact_tools, phase="d-context-1", action="重复装载业务资料（第 1 次）"
    )
    second = ctx.call_tools(
        scenario.fact_tools,
        phase="d-context-2",
        action="重复装载业务资料（第 2 次，与第 1 次内容完全相同）",
    )

    # 同一份上下文重复粘贴多次，再连同两批重复的工具结果一起塞进去。
    heavy_context = "\n\n".join(
        [scenario.materials_block()] * D_CONTEXT_REPEAT
        + [_fact_block(ctx, first), _fact_block(ctx, second)]
    )
    heavy_user = (
        f"客户原话：\n{ctx.request_text}\n\n"
        f"当前可用业务资料与工具结果：\n{heavy_context}\n\n"
        "请解析为结构化需求并给出候选方案。"
    )

    parsed = ctx.ask(
        phase="d-parse-1",
        action=f"解析客户需求（上下文重复粘贴 {D_CONTEXT_REPEAT} 份）",
        user=heavy_user,
    )
    ctx.ask(
        phase="d-parse-2",
        action="重复解析同一需求（与上一步等价）",
        user=heavy_user,
    )

    strong_model = ctx.config.strong_model
    judge_user = (
        f"需求解析：\n{parsed}\n\n"
        f"当前可用业务资料与工具结果：\n{heavy_context}\n\n"
        "请给出候选方案与必须停下来的人工确认点。"
    )
    strong = ctx.ask(
        phase="d-judge-strong",
        action="用更强模型重复同一判断",
        user=judge_user,
        model=strong_model,
    )
    if not strong_model:
        ctx.notes.append(
            "未配置 LLM_STRONG_MODEL：本步回退到同一模型，「不必要的强模型」这一项不成立，"
            "D 档的额外消耗全部来自重复上下文与重复步骤。"
        )
    ctx.ask(
        phase="d-judge-dup",
        action="重复执行同一判断（与上一步等价）",
        user=judge_user,
    )

    verify_user = (
        f"待校验草稿：\n{strong}\n\n"
        f"事实依据：\n{heavy_context}\n\n"
        "逐条检查草稿：凡是没有可核验来源的船期、运价、舱位承诺，一律改为「待业务资料 / 人工确认」。"
        "然后输出修订后的草稿。"
    )
    ctx.ask(phase="d-verify-1", action="重复校验（第 1 次）", user=verify_user)
    checked = ctx.ask(
        phase="d-verify-2",
        action="重复校验（第 2 次，与第 1 次完全相同）",
        user=verify_user,
    )

    output = ctx.ask(
        phase="d-deliver",
        action="形成可交付结果与停止点",
        status="waiting_human",
        user=(
            f"已校验内容：\n{checked}\n\n"
            "请输出最终可交付结果：先给结论，再给缺失条件与下一步动作，最后列出人工确认点。"
        ),
    )

    ctx.notes.append(
        f"D 档与 C 档业务目标相同，但真实执行了 {D_CONTEXT_REPEAT} 份重复上下文、"
        "一次重复的资料装载、一次重复解析、一次重复判断与一次重复校验。"
        "对比 C 档的模型调用、工具调用与输入 Token，差额即为可解释的低效消耗。"
    )
    return output, "waiting_human"


MODE_RUNNERS = {
    "A": run_mode_a,
    "B": run_mode_b,
    "C": run_mode_c,
    "D": run_mode_d,
}


# --------------------------------------------------------------------------
# structure-only chains (no provider configured)
# --------------------------------------------------------------------------


def _structural_chain(scenario: Scenario, mode: str) -> list[tuple[str, str, int]]:
    """(phase, action, tool_calls) for a mode, without executing anything."""
    fact_tools = len(scenario.fact_tools)
    all_tools = len(scenario.tools)
    if mode == "A":
        return [("direct", "直接回答客户问题", 0)]
    if mode == "B":
        return [
            ("context", "装载当前可用业务资料", all_tools),
            ("answer", "基于全量上下文生成可交付结果", 0),
        ]
    if mode == "C":
        return [
            ("parse", "解析客户需求", 0),
            ("gaps", "判断缺口", 0),
            ("facts", "获取可核验业务事实", fact_tools),
            ("judge", "业务判断与人工确认点", 0),
            ("verify", "校验：不得把未核验资料写成事实", 0),
            ("deliver", "形成可交付结果与停止点", 0),
        ]
    return [
        ("d-context-1", "重复装载业务资料（第 1 次）", fact_tools),
        ("d-context-2", "重复装载业务资料（第 2 次，与第 1 次内容完全相同）", fact_tools),
        ("d-parse-1", f"解析客户需求（上下文重复粘贴 {D_CONTEXT_REPEAT} 份）", 0),
        ("d-parse-2", "重复解析同一需求（与上一步等价）", 0),
        ("d-judge-strong", "用更强模型重复同一判断", 0),
        ("d-judge-dup", "重复执行同一判断（与上一步等价）", 0),
        ("d-verify-1", "重复校验（第 1 次）", 0),
        ("d-verify-2", "重复校验（第 2 次，与第 1 次完全相同）", 0),
        ("d-deliver", "形成可交付结果与停止点", 0),
    ]


def structural_steps(scenario: Scenario, mode: str) -> list[StepRecord]:
    steps = []
    for index, (phase, action, tool_calls) in enumerate(_structural_chain(scenario, mode), start=1):
        steps.append(
            StepRecord(
                step=index,
                action=action,
                phase=phase,
                status="not_executed",
                tool_calls=tool_calls,
                detail="未执行：本次没有可用的 provider",
            )
        )
    return steps


# --------------------------------------------------------------------------
# engine
# --------------------------------------------------------------------------


def aggregate(steps: list[StepRecord]) -> UsageSummary:
    """Sum the run from its steps. Nothing is invented where a step is silent."""
    model_calls = sum(1 for step in steps if step.model)
    tool_calls = sum(step.tool_calls for step in steps)

    input_tokens: int | None = None
    output_tokens: int | None = None
    cached_tokens: int | None = None
    latency_ms: int | None = None

    for step in steps:
        if step.input_tokens is not None:
            input_tokens = (input_tokens or 0) + step.input_tokens
        if step.output_tokens is not None:
            output_tokens = (output_tokens or 0) + step.output_tokens
        # A provider that reports no cache accounting leaves this None for the
        # whole run — a missing measurement is not a cache miss.
        if step.cached_tokens is not None:
            cached_tokens = (cached_tokens or 0) + step.cached_tokens
        if step.latency_ms is not None:
            latency_ms = (latency_ms or 0) + step.latency_ms

    total_tokens = None
    if input_tokens is not None and output_tokens is not None:
        total_tokens = input_tokens + output_tokens

    return UsageSummary(
        model_calls=model_calls,
        tool_calls=tool_calls,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_tokens=cached_tokens,
        total_tokens=total_tokens,
        latency_ms=latency_ms,
    )


class RunEngine:
    def __init__(self, provider: OpenAICompatibleProvider, config: ProviderConfig):
        self.provider = provider
        self.config = config

    def execute(self, *, scenario: Scenario, mode: str, request_text: str) -> RunRecord:
        identity = {
            "run_id": str(uuid4()),
            "created_at": utc_now_iso(),
            "scenario": scenario.key,
            "scenario_name": scenario.name,
            "mode": mode,
            "mode_label": MODE_LABELS[mode],
            "request_text": request_text,
            "task": scenario.task,
            "known": list(scenario.known),
            "missing": list(scenario.missing),
            "next_actions": list(scenario.next_actions),
            "human_gates": list(scenario.human_gates),
            "dependencies": scenario.dependency_list(),
            "provider": self.config.public(),
        }

        if not self.provider.configured:
            steps = structural_steps(scenario, mode)
            return RunRecord(
                **identity,
                steps=steps,
                usage=aggregate(steps),
                run_status="not_executed",
                evidence_level="structure_only",
                notes=[
                    "未配置 provider（缺少 "
                    + "、".join(self.config.missing_settings)
                    + "）：本次只输出结构示例，所有 Token 字段为 null，不伪造数字。",
                    "设置 LLM_BASE_URL / LLM_API_KEY / LLM_MODEL 后可执行真实运行并留存 usage。",
                    "无 provider 时仍可回放仓库内已保存的运行记录。",
                ],
            )

        ctx = RunContext(
            scenario=scenario,
            mode=mode,
            request_text=request_text,
            provider=self.provider,
            config=self.config,
            toolbox=ToolBox(scenario=scenario),
        )

        try:
            output, run_status = MODE_RUNNERS[mode](ctx)
        except StepFailure as failure:
            return RunRecord(
                **identity,
                steps=ctx.steps,
                usage=aggregate(ctx.steps),
                run_status="error",
                evidence_level="live",
                notes=ctx.notes,
                error=str(failure),
            )

        return RunRecord(
            **identity,
            steps=ctx.steps,
            usage=aggregate(ctx.steps),
            output=output,
            run_status=run_status,
            evidence_level="live",
            claim_audit=audit_claims(output),
            notes=ctx.notes,
        )
