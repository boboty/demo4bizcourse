"""Run-record contract shared by the engine, the store and the browser.

Field names are the classroom vocabulary from AGENTS.md: step / action / model /
input_tokens / output_tokens / cached_tokens / tool_calls / latency_ms / status.
Nothing scenario-specific appears here — a new business scenario reuses this
model unchanged.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field, model_validator

# ok            — the step did its job
# blocked       — an external dependency (fact, permission, capacity) is missing
# waiting_human — the step ended at a gate only a person can clear
# error         — the call itself failed
# skipped       — the chain stopped before reaching this step
# not_executed  — no provider configured; the step is shown as structure only
STEP_STATUSES = ("ok", "blocked", "waiting_human", "error", "skipped", "not_executed")

# How a completion ended, as the provider reports it. A call stopped by the
# output cap did not finish — what it wrote is a prefix of what it was saying,
# and no Token figure makes that text complete.
TRUNCATING_FINISH_REASONS = ("length", "max_tokens")

# Output completeness is a *different claim* from token measurement. A run can
# have perfectly measured usage for text that was cut off mid-sentence, so the
# two are recorded separately and never collapsed into one "ready" flag.
#   complete     — every model call reported an ending that was not the cap
#   truncated    — at least one call hit the output cap (finish_reason=length)
#   unknown      — a call happened but the provider reported no finish_reason,
#                  so completeness cannot be claimed either way
#   not_executed — no model call happened
OUTPUT_EVIDENCE_LEVELS = ("complete", "truncated", "unknown", "not_executed")


def output_evidence_for(steps: list["StepRecord"]) -> str:
    """Did the calls that produced this output actually finish?

    Returns one of ``OUTPUT_EVIDENCE_LEVELS``. A missing ``finish_reason`` is
    *not* read as "stopped normally": a gateway that says nothing has left the
    output's completeness unproven, and calling that complete is exactly the
    mistake this level exists to prevent.
    """
    model_steps = [step for step in steps if step.model]
    if not model_steps:
        return "not_executed"
    if any(step.truncated for step in model_steps):
        return "truncated"
    if any(step.finish_reason is None for step in model_steps):
        return "unknown"
    return "complete"


# live          — real model calls happened
# structure_only— no provider configured; the chain shape is shown, numbers are null
EVIDENCE_LEVELS = ("live", "structure_only")

# A tool returning something is not the same as the business fact being usable.
# `missing` and `unverified` both block a step whose job is to obtain verifiable
# facts; only `verified` counts as obtained.
FACT_STATES = ("missing", "unverified", "verified")
FACT_STATE_LABELS = {
    "missing": "无结果",
    "unverified": "有结果但未核验",
    "verified": "可核验结果",
}

# Execution evidence and token evidence are different claims. A run may really
# have called a model while the provider reported no usage at all — that is a
# real run, but it cannot be used as a Token teaching record.
#   measured     — every model call reported input and output tokens
#   partial      — some calls reported usage, some did not
#   not_reported — calls happened, no usage came back
#   not_executed — no model call happened
TOKEN_EVIDENCE_LEVELS = ("measured", "partial", "not_reported", "not_executed")


class FactState(BaseModel):
    """Per-tool outcome of a fact-gathering step."""

    name: str
    title: str
    state: str
    state_label: str
    note: str | None = None


class StepRecord(BaseModel):
    step: int
    action: str
    phase: str
    status: str = "ok"
    model: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cached_tokens: int | None = None
    tool_calls: int = 0
    tools: list[str] = Field(default_factory=list)
    facts: list[FactState] | None = None
    latency_ms: int | None = None
    result: str | None = None
    detail: str | None = None
    usage_raw: dict | None = None
    # How the provider said this call ended, verbatim (lower-cased), or None
    # when it did not say. `truncated` is derived from it below, never set
    # independently, so the two can never disagree in a saved record.
    finish_reason: str | None = None
    truncated: bool = False

    @model_validator(mode="after")
    def _derive_truncation(self) -> "StepRecord":
        self.truncated = self.finish_reason in TRUNCATING_FINISH_REASONS
        return self


class UsageSummary(BaseModel):
    """Run-level totals.

    Token fields stay ``None`` when no model call reported them. ``cached_tokens``
    stays ``None`` unless at least one response actually carried cache
    accounting — an unmeasured cache is never rendered as a zero hit rate.
    """

    model_calls: int = 0
    tool_calls: int = 0
    input_tokens: int | None = None
    output_tokens: int | None = None
    cached_tokens: int | None = None
    total_tokens: int | None = None
    latency_ms: int | None = None


class ClaimAudit(BaseModel):
    """A keyword scan over the produced text, not a fact check.

    It exists so the instructor can point at a concrete sentence in mode A/B
    without having to re-read the whole output live. It proves nothing.
    """

    method: str = "keyword_heuristic"
    disclaimer: str = "关键词启发式扫描，不是事实核验；只用于课堂定位，不作为结论。"
    price_mentions: list[str] = Field(default_factory=list)
    schedule_mentions: list[str] = Field(default_factory=list)
    verdict: str = "unscanned"


class RunRecord(BaseModel):
    run_id: str
    created_at: str
    # One experiment = one A/B/C/D batch over the same task and input.
    experiment_id: str | None = None
    scenario: str
    scenario_name: str
    mode: str
    mode_label: str
    request_text: str
    # The scenario's own opening line, kept so a record can tell whether the
    # instructor swapped the input (the preset baseline no longer applies).
    scenario_request_text: str = ""
    task: str
    # 场景验收基准 — written before the run, used to compare against what the
    # model actually produced. It is NOT this run's output.
    known: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    human_gates: list[str] = Field(default_factory=list)
    # Tool / material dependencies at the time of the run, so a saved record can
    # be replayed offline without consulting the scenario registry.
    dependencies: list[dict] = Field(default_factory=list)
    steps: list[StepRecord] = Field(default_factory=list)
    usage: UsageSummary = Field(default_factory=UsageSummary)
    output: str | None = None
    run_status: str = "ok"
    evidence_level: str = "structure_only"
    token_evidence: str = "not_executed"
    # Output completeness, derived from the steps below. Kept as its own axis:
    # usage can be perfectly measured for text the output cap cut in half.
    output_evidence: str = "not_executed"
    truncated_steps: list[int] = Field(default_factory=list)
    provider: dict | None = None
    claim_audit: ClaimAudit | None = None
    notes: list[str] = Field(default_factory=list)
    error: str | None = None

    @model_validator(mode="after")
    def _derive_output_completeness(self) -> "RunRecord":
        # Derived, so a record loaded back from runs/ reports truncation from
        # its own steps — including records written before this field existed,
        # which come back as `unknown` rather than as falsely complete.
        self.output_evidence = output_evidence_for(self.steps)
        self.truncated_steps = [step.step for step in self.steps if step.truncated]
        return self

    @property
    def classroom_ready(self) -> bool:
        """Usable as a Token teaching record: really executed, usage measured.

        This answers one question only — 数字是否计量完整. Whether the output
        itself finished is a separate question, answered by `output_evidence`.
        """
        return (
            self.evidence_level == "live"
            and self.token_evidence == "measured"
            and self.usage.input_tokens is not None
            and self.usage.output_tokens is not None
        )

    @property
    def freeze_ready(self) -> bool:
        """适合课堂冻结：Token 读数完整，**并且**没有输出被长度上限截断。

        Deliberately a second, independent check rather than a tightening of
        `classroom_ready`: 一组数字可以「计量完整但输出不完整」，把两者
        合并会掩盖这种记录，正是本次要避免的。
        """
        return self.classroom_ready and self.output_evidence == "complete"


class RecordSummary(BaseModel):
    """Row shape for the replay picker and the comparison table."""

    run_id: str
    created_at: str
    experiment_id: str | None = None
    scenario: str
    scenario_name: str
    mode: str
    mode_label: str
    evidence_level: str
    token_evidence: str
    run_status: str
    model_calls: int
    tool_calls: int
    input_tokens: int | None = None
    output_tokens: int | None = None
    cached_tokens: int | None = None
    total_tokens: int | None = None
    latency_ms: int | None = None
    # Token 计量完整 ≠ 输出完整：对照表两列都要有，才能看出某档是不是被截断。
    classroom_ready: bool = False
    output_evidence: str = "not_executed"
    truncated_calls: int = 0
    freeze_ready: bool = False
    request_text: str


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def summarise(record: RunRecord) -> RecordSummary:
    return RecordSummary(
        run_id=record.run_id,
        created_at=record.created_at,
        experiment_id=record.experiment_id,
        scenario=record.scenario,
        scenario_name=record.scenario_name,
        mode=record.mode,
        mode_label=record.mode_label,
        evidence_level=record.evidence_level,
        token_evidence=record.token_evidence,
        run_status=record.run_status,
        model_calls=record.usage.model_calls,
        tool_calls=record.usage.tool_calls,
        input_tokens=record.usage.input_tokens,
        output_tokens=record.usage.output_tokens,
        cached_tokens=record.usage.cached_tokens,
        total_tokens=record.usage.total_tokens,
        latency_ms=record.usage.latency_ms,
        classroom_ready=record.classroom_ready,
        output_evidence=record.output_evidence,
        truncated_calls=len(record.truncated_steps),
        freeze_ready=record.freeze_ready,
        request_text=record.request_text,
    )
