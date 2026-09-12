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
from collections.abc import Callable
from dataclasses import dataclass, field
from uuid import uuid4

from .config import ProviderConfig
from .models import (
    FACT_STATE_LABELS,
    ClaimAudit,
    RunRecord,
    StepRecord,
    UsageSummary,
    output_evidence_for,
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

# Output budgets, in Chinese characters, per step kind. `max_tokens` is the hard
# cap the provider enforces; these are the soft limits written into the prompt
# so a normal run finishes well inside it. Without them the pass-through steps
# (判断缺口 / 校验) restate their whole input and end up at the cap, which means
# the Token numbers record how much padding the prompt invited rather than how
# much work the step did.
BUDGET_PARSE = 150
BUDGET_GAPS = 150
BUDGET_JUDGE = 250
BUDGET_VERIFY = 250
BUDGET_DELIVER = 400
# A / B answer the customer directly; same delivery budget as C's 输出 step.
BUDGET_DIRECT = 400

_CONCISE = "只给结论，不复述输入或题目，不展开推理过程。"


def _budget(instruction: str, limit: int) -> str:
    """Append the step's output budget to its instruction.

    Kept next to the step that uses it rather than in the scenario: how long an
    answer may be is an engine-level measurement decision, not business content.
    """
    return f"{instruction}\n{_CONCISE}总字数不超过 {limit} 字。"


# 两类信息必须分开对待，否则「没有可核验来源就写待业务资料」这条规则会被无差别
# 执行，把客户自己已经说清楚的港口、箱型箱量一起抹掉——校验步骤一旦这么改写，
# 后面只拿到校验稿的交付步骤就再也拿不回这些条件。客户说过的任务是任务的输入，
# 不是等待外部核验的事实。
CUSTOMER_INPUT_RULE = (
    "两类信息必须分开处理：\n"
    "（一）客户明确陈述的任务输入（起运港、目的港、箱型箱量、货好时间等）："
    "是客户给出的条件，直接按客户口径保留，不需要承运人或其他外部来源核验，"
    "不得改写成「待确认」或「待业务资料」。\n"
    "（二）外部业务事实（真实船期、运价、附加费、舱位等）：必须有可核验来源；"
    "没有来源的一律写「待业务资料 / 人工确认」，不得给数字或作承诺。\n"
    "客户只给了相对时间（如「下周三」）时，按客户口径保留即可；"
    "确实需要落到具体日期时，只能写「具体日期待确认」。"
)


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
    # 可选的两个观察者，供 Demo 1 的实时执行视图使用。它们只是旁观——不参与
    # 执行、不改变调用顺序、不影响任何记录下来的数字，也不影响记录格式。
    #
    # 为什么「开始」也要观察：页面上那句「正在理解客户需求……」必须是真的开始
    # 执行了，而不是前端看到上一步结束就推断下一步在跑。
    on_step_start: Callable[[int, str, str], None] | None = None
    on_step: Callable[[StepRecord], None] | None = None

    def _begin(self, phase: str, action: str) -> None:
        if self.on_step_start is not None:
            self.on_step_start(self._next_index(), phase, action)

    def _record(self, step: StepRecord) -> None:
        self.steps.append(step)
        if self.on_step is not None:
            self.on_step(step)

    @property
    def system_prompt(self) -> str:
        rules = self.scenario.rules_block()
        parts = [self.scenario.persona, f"业务目标：{self.scenario.task}"]
        if rules:
            parts.append("硬性要求：\n" + rules)
        parts.append(f"输出要求：{_CONCISE}")
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
        self._begin(phase, action)
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
            self._record(failure_step)
            raise StepFailure(str(exc), failure_step) from exc

        self._record(
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
                # Only the provider's own reason is recorded; `truncated` is
                # derived from it on the record, so the two cannot drift.
                finish_reason=result.finish_reason,
            )
        )
        self.texts[phase] = result.text
        return result.text

    def call_tools(self, names, *, phase: str, action: str) -> list[ToolCall]:
        """Invoke tools and record the batch as one step with no model call.

        The step carries each tool's fact state, so "we got something back" and
        "we got something usable" stay distinguishable in the record.
        """
        self._begin(phase, action)
        calls = self.toolbox.call_many(list(names))
        self._record(
            StepRecord(
                step=self._next_index(),
                action=action,
                phase=phase,
                status="ok",
                tool_calls=len(calls),
                tools=[call.name for call in calls],
                facts=[call.to_fact_state() for call in calls],
                latency_ms=0,
                detail="、".join(
                    f"{call.title}={FACT_STATE_LABELS[call.fact_state]}" for call in calls
                ),
            )
        )
        return calls

    def patch_last_step(self, **fields) -> None:
        step = self.steps[-1]
        for key, value in fields.items():
            setattr(step, key, value)
        # 这一步的结论是现在才定下来的（工具拿到了东西 ≠ 能用），观察者要看到
        # 修订后的版本，而不是修订前那个还没判断完的样子。
        if self.on_step is not None:
            self.on_step(step)


# --------------------------------------------------------------------------
# mode runners
# --------------------------------------------------------------------------


def _fact_block(ctx: RunContext, calls: list[ToolCall]) -> str:
    """Tool results plus an explicit statement of which ones are usable.

    Without this the model sees a schedule payload and treats it as a fact; the
    state line is what keeps 有结果 and 能用 apart in the prompt too, not just
    in the record.
    """
    if not calls:
        return ctx.toolbox.render(calls)
    lines = "\n".join(
        f"- {call.title}：{FACT_STATE_LABELS[call.fact_state]}"
        + (f"（{call.state_note}）" if call.state_note else "")
        for call in calls
    )
    return f"工具结果状态：\n{lines}\n\n{ctx.toolbox.render(calls)}"


def run_mode_a(ctx: RunContext) -> tuple[str, str]:
    """A 直接回答 — customer's raw words, nothing else, asked for a deliverable."""
    output = ctx.ask(
        phase="direct",
        action="直接回答客户问题",
        user=ctx.request_text,
        system=_budget(
            f"{ctx.scenario.persona}\n\n"
            "请直接给出客户可交付的结果。不要描述你的推理过程，不要向客户反问。"
            "简洁、可直接发送给客户。",
            BUDGET_DIRECT,
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
            + _budget(
                "请基于以上全部资料，形成可交付结果。简洁、可直接发送给客户，"
                "不要复述资料原文。",
                BUDGET_DIRECT,
            )
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
            + _budget(
                "请解析为结构化需求：起运港、目的港、箱型箱量、货好时间、客户期望。"
                "只输出这几项结构化字段，每项一行，不要编造客户没说的条件。",
                BUDGET_PARSE,
            )
        ),
    )

    gaps = ctx.ask(
        phase="gaps",
        action="判断缺口",
        user=(
            f"需求解析：\n{parsed}\n\n"
            f"当前可用资料清单：\n{scenario.materials_block()}\n\n"
            + _budget(
                "要完成这件任务，还缺哪些只能由外部事实或人工确认补上的条件？"
                "只列缺口，每条一行，不要编造内容，不要解释为什么缺。",
                BUDGET_GAPS,
            )
        ),
    )

    fact_calls = ctx.call_tools(
        scenario.fact_tools, phase="facts", action="获取可核验业务事实"
    )
    unusable = ctx.toolbox.unusable_facts()
    if unusable:
        # 「拿到了」和「能用」是两回事：未核验的教学构造数据同样不能让这一步成立。
        ctx.patch_last_step(
            status="blocked",
            detail=(
                "未取得可核验事实：" + "、".join(spec.title for spec in unusable)
                + f"（共 {len(scenario.fact_tools)} 项）"
            ),
        )
    else:
        ctx.patch_last_step(detail="全部事实来源均已核验")
    fact_block = _fact_block(ctx, fact_calls)

    judgment = ctx.ask(
        phase="judge",
        action="业务判断与人工确认点",
        user=(
            f"需求解析：\n{parsed}\n\n"
            f"已识别缺口：\n{gaps}\n\n"
            f"已取回事实（注意每条的 provenance 与 verified 标记）：\n{fact_block}\n\n"
            + _budget(
                "请给出候选方案与必须停下来的人工确认点。"
                "没有可核验来源的数字一律写「待业务资料」。",
                BUDGET_JUDGE,
            )
        ),
    )

    checked = ctx.ask(
        phase="verify",
        action="校验：不得把未核验资料写成事实",
        user=(
            f"待校验草稿：\n{judgment}\n\n"
            f"事实依据：\n{fact_block}\n\n"
            + _budget(
                f"{CUSTOMER_INPUT_RULE}\n"
                "逐条检查草稿：凡是没有可核验来源的船期、运价、舱位承诺，"
                "一律改为「待业务资料 / 人工确认」；客户已经明确陈述的任务输入"
                "不在其列，必须原样保留。只输出修订后的草稿，不要逐条解释改动过程。",
                BUDGET_VERIFY,
            )
        ),
    )

    output = ctx.ask(
        phase="deliver",
        action="形成可交付结果与停止点",
        status="waiting_human",
        user=(
            f"客户原话：\n{ctx.request_text}\n\n"
            f"已解析需求：\n{parsed}\n\n"
            f"已校验内容：\n{checked}\n\n"
            + _budget(
                f"{CUSTOMER_INPUT_RULE}\n"
                "请输出最终可交付结果：先给结论，再给缺失条件与下一步动作，"
                "最后列出人工确认点。客户已经明确给出的条件必须原样保留，"
                "不得因为「没有来源核验」就把它们改写成待确认。",
                BUDGET_DELIVER,
            )
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
    unusable = ctx.toolbox.unusable_facts()
    if unusable:
        # 业务结果与 C 档一致：拿到的东西不能当事实用。低效的是过程，不是结论。
        ctx.patch_last_step(
            status="blocked",
            detail="未取得可核验事实：" + "、".join(spec.title for spec in unusable),
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
        # D 档的浪费必须是「真实重复的上下文」，不是「被提示词邀请的长输出」：
        # 与 C 档一样的字数上限，重复步骤才只重复它该重复的那部分。
        + _budget(
            "请解析为结构化需求并给出候选方案。解析部分只输出结构化字段。",
            BUDGET_JUDGE,
        )
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
        + _budget("请给出候选方案与必须停下来的人工确认点。", BUDGET_JUDGE)
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
        + _budget(
            f"{CUSTOMER_INPUT_RULE}\n"
            "逐条检查草稿：凡是没有可核验来源的船期、运价、舱位承诺，"
            "一律改为「待业务资料 / 人工确认」；客户已经明确陈述的任务输入"
            "不在其列，必须原样保留。只输出修订后的草稿。",
            BUDGET_VERIFY,
        )
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
            f"客户原话：\n{ctx.request_text}\n\n"
            f"已解析需求：\n{parsed}\n\n"
            f"已校验内容：\n{checked}\n\n"
            + _budget(
                f"{CUSTOMER_INPUT_RULE}\n"
                "请输出最终可交付结果：先给结论，再给缺失条件与下一步动作，"
                "最后列出人工确认点。客户已经明确给出的条件必须原样保留，"
                "不得因为「没有来源核验」就把它们改写成待确认。",
                BUDGET_DELIVER,
            )
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


def token_evidence_for(steps: list[StepRecord]) -> str:
    """Did the provider actually report token usage for the calls it served?

    A run that really called a model but got no `usage` back is still a real
    run — it just is not a Token teaching record, and the two must not be
    counted as the same thing when the instructor prepares the class.
    """
    model_steps = [step for step in steps if step.model]
    if not model_steps:
        return "not_executed"
    measured = sum(
        1
        for step in model_steps
        if step.input_tokens is not None and step.output_tokens is not None
    )
    if measured == len(model_steps):
        return "measured"
    return "partial" if measured else "not_reported"


class RunEngine:
    def __init__(self, provider: OpenAICompatibleProvider, config: ProviderConfig):
        self.provider = provider
        self.config = config

    def execute(
        self,
        *,
        scenario: Scenario,
        mode: str,
        request_text: str,
        experiment_id: str | None = None,
        run_id: str | None = None,
        on_step_start: Callable[[int, str, str], None] | None = None,
        on_step: Callable[[StepRecord], None] | None = None,
    ) -> RunRecord:
        # run_id 可以由调用方给定：Demo 1 需要在执行开始前就把「本次运行」的
        # 身份交给页面，执行结束后 Demo 2 重放的就是同一条记录。不传时行为与
        # 以前完全一样，记录格式也没有变化。
        identity = {
            "run_id": run_id or str(uuid4()),
            "created_at": utc_now_iso(),
            "experiment_id": experiment_id,
            "scenario": scenario.key,
            "scenario_name": scenario.name,
            "mode": mode,
            "mode_label": MODE_LABELS[mode],
            "request_text": request_text,
            "scenario_request_text": scenario.request_text,
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
                token_evidence="not_executed",
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
            on_step_start=on_step_start,
            on_step=on_step,
        )

        try:
            output, run_status = MODE_RUNNERS[mode](ctx)
        except StepFailure as failure:
            return self._live_record(
                identity, ctx, run_status="error", error=str(failure)
            )

        return self._live_record(
            identity,
            ctx,
            run_status=run_status,
            output=output,
            claim_audit=audit_claims(output),
        )

    def _live_record(
        self,
        identity: dict,
        ctx: RunContext,
        *,
        run_status: str,
        output: str | None = None,
        claim_audit: ClaimAudit | None = None,
        error: str | None = None,
    ) -> RunRecord:
        notes = list(ctx.notes)
        token_evidence = token_evidence_for(ctx.steps)
        output_evidence = output_evidence_for(ctx.steps)
        if output_evidence == "truncated":
            cut = [step.step for step in ctx.steps if step.truncated]
            notes.append(
                "输出不完整：第 "
                + "、".join(str(index) for index in cut)
                + " 步的模型调用因为长度上限被截断（finish_reason=length），"
                "写下来的只是模型当时想说的前半段。这几次调用的 Token 读数依然真实，"
                "但不能当作正常完整结果使用。"
            )
        elif output_evidence == "unknown":
            notes.append(
                "provider 没有返回 finish_reason：本次无法确认每个调用是正常结束还是被截断，"
                "输出的完整性未获证明。"
            )
        if token_evidence == "not_reported":
            notes.append(
                "provider 没有返回 usage：这次是真实模型调用，但没有 Token 读数，"
                "不能作为 Token 实验记录使用。"
            )
        elif token_evidence == "partial":
            notes.append(
                "只有部分模型调用返回了 usage：Token 合计不完整，只能作为参考。"
            )
        return RunRecord(
            **identity,
            steps=ctx.steps,
            usage=aggregate(ctx.steps),
            output=output,
            run_status=run_status,
            evidence_level="live",
            token_evidence=token_evidence,
            claim_audit=claim_audit,
            notes=notes,
            error=error,
        )
