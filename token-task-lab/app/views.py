"""Front / back projections of a run record.

AGENTS.md forbids Demo 1 from displaying token numbers. Rather than trusting the
page to leave them out, the API hands Demo 1 a projection that does not contain
them: `front_view` is built from an allow-list, so a new field added to the
record can never leak into the business-facing half by accident.
"""

from __future__ import annotations

from .models import RunRecord

# Everything Demo 1 is allowed to see — business structure only.
FRONT_FIELDS = (
    "run_id",
    "created_at",
    "scenario",
    "scenario_name",
    "mode",
    "mode_label",
    "request_text",
    "task",
    "known",
    "missing",
    "next_actions",
    "human_gates",
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
)


def front_view(record: RunRecord) -> dict:
    """Demo 1 业务正面：无 Token、无步骤、无调用次数。"""
    payload = record.model_dump(include=set(FRONT_FIELDS))
    return payload


def back_view(record: RunRecord) -> dict:
    """Demo 2 运行背面：步骤、usage、输出与异常。"""
    return record.model_dump()
