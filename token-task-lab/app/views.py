"""Front / back projections of a run record.

Two rules this module exists to enforce.

1. Demo 1 must never show a token number. `front_view` is built from an
   allow-list, so a new field on the record cannot leak into the business half
   by accident.

2. Demo 1 must show what *this run* produced, not what the scenario file says.
   The scenario's `known` / `missing` / `next_actions` are written before any
   model runs — presenting them as the model's work would make the second
   lecture's claim ("watch the AI break the task down") false. They are still
   shown, but only as an explicitly labelled 场景验收基准 to compare against,
   while the main area renders `observations`: the actual parse / gaps / facts /
   judge / deliver output of this run.
"""

from __future__ import annotations

from .models import RunRecord

# Everything Demo 1 is allowed to see. Deliberately excludes the preset
# baseline fields — those travel inside `baseline` so the page has to label
# them as pre-written rather than free to render them as "the AI's answer".
FRONT_FIELDS = (
    "run_id",
    "created_at",
    "scenario",
    "scenario_name",
    "mode",
    "mode_label",
    "request_text",
    "task",
    "dependencies",
    "evidence_level",
    "run_status",
)

# Field names that must never appear in a front view, checked by the test suite.
FORBIDDEN_IN_FRONT = (
    "usage",
    "steps",
    "model",
    "input_tokens",
    "output_tokens",
    "cached_tokens",
    "total_tokens",
    "latency_ms",
    "model_calls",
    "tool_calls",
    "claim_audit",
    "usage_raw",
    "provider",
    "token_evidence",
    "usage_summary",
)

# Which chain step answers which Demo 1 question. The low-efficiency mode's
# repeated phases map onto the same questions as their C-mode counterparts —
# D differs in cost, not in business content.
OBSERVATION_PHASES: dict[str, tuple[str, str]] = {
    "direct": ("result", "AI 直接给出的结果"),
    "answer": ("result", "AI 基于全量上下文的回答"),
    "parse": ("understanding", "AI 实际任务理解"),
    "d-parse-1": ("understanding", "AI 实际任务理解"),
    "gaps": ("gaps", "AI 实际识别缺口"),
    "facts": ("facts", "本次事实获取结果"),
    "d-context-1": ("facts", "本次事实获取结果"),
    "judge": ("judgment", "AI 业务判断与人工确认点"),
    "d-judge-strong": ("judgment", "AI 业务判断与人工确认点"),
    "verify": ("verification", "AI 校验结果"),
    "d-verify-1": ("verification", "AI 校验结果"),
    "deliver": ("delivery", "最终结论与停止点"),
    "d-deliver": ("delivery", "最终结论与停止点"),
}


def observations_for(record: RunRecord) -> list[dict]:
    """This run's own business output, step by step, with no token data."""
    observations = []
    for step in record.steps:
        mapped = OBSERVATION_PHASES.get(step.phase)
        if mapped is None:
            # A deliberate D-mode duplicate, or a structural placeholder.
            continue
        role, label = mapped
        observations.append(
            {
                "role": role,
                "label": label,
                "phase": step.phase,
                "action": step.action,
                "status": step.status,
                "text": step.result,
                "facts": [fact.model_dump() for fact in (step.facts or [])],
                "executed": step.status != "not_executed",
            }
        )
    return observations


def baseline_for(record: RunRecord) -> dict:
    """场景验收基准 — written before the run, shown for comparison only."""
    matches = record.request_text.strip() == (record.scenario_request_text or "").strip()
    return {
        "label": "场景验收基准",
        "note": (
            "课前写定的场景答案，用来和本次实际识别结果对照。"
            "它不是本次运行产生的，不能当作 AI 的输出展示。"
        ),
        "matches_request": matches,
        "mismatch_note": None
        if matches
        else "本次输入与场景原始请求不一致，下面的基准已不适用，只看上方实际结果。",
        "scenario_request_text": record.scenario_request_text,
        "known": list(record.known),
        "missing": list(record.missing),
        "next_actions": list(record.next_actions),
        "human_gates": list(record.human_gates),
    }


def front_view(record: RunRecord) -> dict:
    """Demo 1 业务正面：本次运行的实际结果 + 场景基准；无 Token、无调用次数。"""
    payload = record.model_dump(include=set(FRONT_FIELDS))
    payload["observations"] = observations_for(record)
    payload["baseline"] = baseline_for(record)
    return payload


def back_view(record: RunRecord) -> dict:
    """Demo 2 运行背面：步骤、usage、输出与异常。"""
    return record.model_dump()
