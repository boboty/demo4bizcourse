"""Tool invocation for the task chain.

Tools here are local and deterministic — the class is studying *why one business
task is not one model call*, not watching a flaky integration. Every call is
still counted and recorded, because the tool-call count is half the point of
Demo 2's header.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from .models import FACT_STATE_LABELS, FactState
from .scenarios.base import Scenario, ToolSpec


@dataclass
class ToolCall:
    name: str
    title: str
    available: bool
    verified: bool
    provenance: str
    payload: dict
    state_note: str | None = None

    @property
    def fact_state(self) -> str:
        if not self.available:
            return "missing"
        if not self.verified:
            return "unverified"
        return "verified"

    @property
    def usable_as_fact(self) -> bool:
        return self.fact_state == "verified"

    def to_fact_state(self) -> FactState:
        return FactState(
            name=self.name,
            title=self.title,
            state=self.fact_state,
            state_label=FACT_STATE_LABELS[self.fact_state],
            note=self.state_note,
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "title": self.title,
            "available": self.available,
            "verified": self.verified,
            "fact_state": self.fact_state,
            "provenance": self.provenance,
            "note": self.state_note,
            "payload": self.payload,
        }


@dataclass
class ToolBox:
    scenario: Scenario
    calls: list[ToolCall] = field(default_factory=list)

    @property
    def tool_calls(self) -> int:
        return len(self.calls)

    def call(self, name: str) -> ToolCall:
        spec = self.scenario.tool(name)
        if spec is None:
            raise KeyError(f"scenario {self.scenario.key!r} has no tool {name!r}")
        call = ToolCall(
            name=spec.name,
            title=spec.title,
            available=spec.available,
            verified=spec.verified,
            provenance=spec.provenance,
            payload=spec.payload,
            state_note=spec.state_note,
        )
        self.calls.append(call)
        return call

    def call_many(self, names: tuple[str, ...] | list[str]) -> list[ToolCall]:
        return [self.call(name) for name in names]

    def unusable_facts(self) -> list[ToolSpec]:
        """Called tools whose result cannot be used as a business fact.

        Both "no result" and "a result nobody can vouch for" leave the step
        short. Treating an unverified fixture as a obtained fact is exactly the
        mistake the step name 获取可核验业务事实 exists to prevent.
        """
        seen: set[str] = set()
        unusable: list[ToolSpec] = []
        for call in self.calls:
            if call.usable_as_fact or call.name in seen:
                continue
            seen.add(call.name)
            spec = self.scenario.tool(call.name)
            if spec is not None:
                unusable.append(spec)
        return unusable

    def render(self, calls: list[ToolCall] | None = None) -> str:
        """Tool output as the model sees it — provenance labels included.

        `calls` defaults to everything invoked so far, which is what a chain
        step wants. The low-efficiency mode passes one batch at a time so that
        a duplicated lookup shows up as a duplicated block instead of being
        silently collapsed.
        """
        selected = self.calls if calls is None else calls
        if not selected:
            return "（本次没有调用工具）"
        blocks = []
        for call in selected:
            blocks.append(
                f"<tool name=\"{call.name}\" available={str(call.available).lower()} "
                f"provenance={call.provenance} verified={str(call.verified).lower()}>\n"
                f"{json.dumps(call.payload, ensure_ascii=False, indent=2)}\n"
                f"</tool>"
            )
        return "\n\n".join(blocks)
