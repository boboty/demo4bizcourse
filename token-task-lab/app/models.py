"""Run-record contract shared by the engine, the store and the browser.

Field names are the classroom vocabulary from AGENTS.md: step / action / model /
input_tokens / output_tokens / cached_tokens / tool_calls / latency_ms / status.
Nothing scenario-specific appears here — a new business scenario reuses this
model unchanged.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

# ok            — the step did its job
# blocked       — an external dependency (fact, permission, capacity) is missing
# waiting_human — the step ended at a gate only a person can clear
# error         — the call itself failed
# skipped       — the chain stopped before reaching this step
# not_executed  — no provider configured; the step is shown as structure only
STEP_STATUSES = ("ok", "blocked", "waiting_human", "error", "skipped", "not_executed")

# live          — numbers came from real provider responses
# structure_only— no provider configured; the chain shape is shown, numbers are null
EVIDENCE_LEVELS = ("live", "structure_only")


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
    latency_ms: int | None = None
    result: str | None = None
    detail: str | None = None
    usage_raw: dict | None = None


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
    scenario: str
    scenario_name: str
    mode: str
    mode_label: str
    request_text: str
    task: str
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
    provider: dict | None = None
    claim_audit: ClaimAudit | None = None
    notes: list[str] = Field(default_factory=list)
    error: str | None = None


class RecordSummary(BaseModel):
    """Row shape for the replay picker — no step bodies, cheap to list."""

    run_id: str
    created_at: str
    scenario: str
    scenario_name: str
    mode: str
    mode_label: str
    evidence_level: str
    run_status: str
    model_calls: int
    tool_calls: int
    input_tokens: int | None = None
    output_tokens: int | None = None
    cached_tokens: int | None = None
    request_text: str


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def summarise(record: RunRecord) -> RecordSummary:
    return RecordSummary(
        run_id=record.run_id,
        created_at=record.created_at,
        scenario=record.scenario,
        scenario_name=record.scenario_name,
        mode=record.mode,
        mode_label=record.mode_label,
        evidence_level=record.evidence_level,
        run_status=record.run_status,
        model_calls=record.usage.model_calls,
        tool_calls=record.usage.tool_calls,
        input_tokens=record.usage.input_tokens,
        output_tokens=record.usage.output_tokens,
        cached_tokens=record.usage.cached_tokens,
        request_text=record.request_text,
    )
