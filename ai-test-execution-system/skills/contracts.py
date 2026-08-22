"""Skill 的统一输入、输出和失败契约。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


class SkillError(RuntimeError):
    """Skill 失败的显式结果；调用方可按 code 记录和验收。"""

    def __init__(
        self,
        skill: str,
        code: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        evidence: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.skill = skill
        self.code = code
        self.context = context or {}
        self.evidence = evidence or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill": self.skill,
            "code": self.code,
            "message": str(self),
            "context": self.context,
            "evidence": self.evidence,
        }


@dataclass
class ExecutionContext:
    """Workflow 在 Skill 之间传递的最小上下文。"""

    base_url: str
    case: Dict[str, Any]
    driver: Any
    evidence_dir: Path
    order_id: Optional[str] = None
    user: Optional[Dict[str, Any]] = None
    record: Dict[str, Any] = field(default_factory=dict)


def nested_get(value: Any, dotted_path: str) -> Any:
    current = value
    for key in dotted_path.split("."):
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def assert_expected_facts(actual: Dict[str, Any], expected: Dict[str, Any], label: str) -> None:
    mismatches = []
    for dotted_path, wanted in expected.items():
        got = nested_get(actual, dotted_path)
        if got != wanted:
            mismatches.append("{0}: 期望 {1!r}，实际 {2!r}".format(dotted_path, wanted, got))
    if mismatches:
        raise AssertionError("{0}断言失败：{1}".format(label, "; ".join(mismatches)))


def require_step(case: Dict[str, Any], step_id: str) -> Dict[str, Any]:
    steps = case.get("ui", {}).get("steps", [])
    matches = [step for step in steps if step.get("id") == step_id]
    if len(matches) != 1:
        raise ValueError("任务必须且只能包含 {0} 步骤。".format(step_id))
    return matches[0]


def skill_error(skill: str, code: str, error: Exception, context: Dict[str, Any]) -> SkillError:
    if isinstance(error, SkillError):
        return error
    return SkillError(skill, code, str(error), context=context)
