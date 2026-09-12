"""The scenario contract.

A scenario supplies business meaning only: who the customer is, what is known,
what is missing, which teaching materials exist, and which tools the chain may
call. The experiment engine never learns the word "船期" — it learns
`fact_tools` and `human_gates`. Adding finance / software-rd / testing /
document-analysis means adding one module here and registering it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..models import FACT_STATE_LABELS


@dataclass(frozen=True)
class Material:
    """A piece of context a mode-B run may paste in wholesale.

    Anything constructed for teaching carries `provenance="teaching_fixture"`
    and `verified=False`, and every rendering of it keeps that label attached.
    """

    key: str
    title: str
    body: str
    provenance: str = "teaching_fixture"
    verified: bool = False


@dataclass(frozen=True)
class ToolSpec:
    """A callable the chain may invoke, backed by a fixed local payload.

    Three outcomes, not two:

    * `missing`    — called, and no business fact could be produced.
    * `unverified` — something came back, but it cannot be used as a business
                     fact (a teaching fixture, a stale export, an unconfirmed
                     source). Having a result is not the same as having a fact.
    * `verified`   — a result the business may actually rely on.

    Both `missing` and `unverified` leave a fact-gathering step short of its
    goal; only `verified` counts as obtained.
    """

    name: str
    title: str
    description: str
    payload: dict
    available: bool = True
    provenance: str = "teaching_fixture"
    verified: bool = False
    # Why this result is or is not usable, in one authored line.
    state_note: str | None = None

    @property
    def tool_calls(self) -> int:
        return 1

    @property
    def fact_state(self) -> str:
        if not self.available:
            return "missing"
        if not self.verified:
            return "unverified"
        return "verified"

    @property
    def fact_state_label(self) -> str:
        return FACT_STATE_LABELS[self.fact_state]

    @property
    def usable_as_fact(self) -> bool:
        return self.fact_state == "verified"


@dataclass(frozen=True)
class Scenario:
    key: str
    name: str
    request_text: str
    task: str
    known: tuple[str, ...]
    missing: tuple[str, ...]
    human_gates: tuple[str, ...]
    next_actions: tuple[str, ...] = ()
    materials: tuple[Material, ...] = ()
    tools: tuple[ToolSpec, ...] = ()
    # Which tools the task-chain "获取事实" step reaches for, in order.
    fact_tools: tuple[str, ...] = ()
    persona: str = "你是一名严谨的企业业务助理。"
    output_rules: tuple[str, ...] = field(default_factory=tuple)

    def tool(self, name: str) -> ToolSpec | None:
        for spec in self.tools:
            if spec.name == name:
                return spec
        return None

    def dependency_list(self) -> list[dict]:
        """场景声明的「工具/资料依赖」——课前写定，不是本次运行的结果。

        `fact_state` 是这里唯一有意义的字段：有结果 ≠ 能用。
        """
        items = [
            {
                "kind": "tool",
                "name": tool.name,
                "title": tool.title,
                "description": tool.description,
                "available": tool.available,
                "verified": tool.verified,
                "fact_state": tool.fact_state,
                "fact_state_label": tool.fact_state_label,
                "provenance": tool.provenance,
                "note": tool.state_note,
            }
            for tool in self.tools
        ]
        items.extend(
            {
                "kind": "material",
                "name": material.key,
                "title": material.title,
                "description": material.body.splitlines()[0],
                "available": True,
                "verified": material.verified,
                "fact_state": "verified" if material.verified else "unverified",
                "fact_state_label": FACT_STATE_LABELS[
                    "verified" if material.verified else "unverified"
                ],
                "provenance": material.provenance,
                "note": "场景声明的资料，未接入真实来源" if not material.verified else None,
            }
            for material in self.materials
        )
        return items

    def rules_block(self) -> str:
        if not self.output_rules:
            return ""
        return "\n".join(f"- {rule}" for rule in self.output_rules)

    def materials_block(self) -> str:
        """Render every available material with its provenance label intact."""
        if not self.materials:
            return "（当前场景没有可用业务资料）"
        chunks = []
        for material in self.materials:
            chunks.append(
                f"### {material.title}\n"
                f"[provenance={material.provenance} verified={str(material.verified).lower()}]\n"
                f"{material.body}"
            )
        return "\n\n".join(chunks)
