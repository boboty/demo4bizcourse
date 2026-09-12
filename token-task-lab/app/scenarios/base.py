"""The scenario contract.

A scenario supplies business meaning only: who the customer is, what is known,
what is missing, which teaching materials exist, and which tools the chain may
call. The experiment engine never learns the word "船期" — it learns
`fact_tools` and `human_gates`. Adding finance / software-rd / testing /
document-analysis means adding one module here and registering it.
"""

from __future__ import annotations

from dataclasses import dataclass, field


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

    `available=False` means the tool was called and the business fact could not
    be produced. That is a normal outcome here, not an error: it is the thing
    the class is watching for.
    """

    name: str
    title: str
    description: str
    payload: dict
    available: bool = True
    provenance: str = "teaching_fixture"
    verified: bool = False

    @property
    def tool_calls(self) -> int:
        return 1


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
        """Demo 1 的「工具/资料依赖」：工具与资料各自能否给出可用结果。"""
        items = [
            {
                "kind": "tool",
                "name": tool.name,
                "title": tool.title,
                "description": tool.description,
                "available": tool.available,
                "verified": tool.verified,
                "provenance": tool.provenance,
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
                "provenance": material.provenance,
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
