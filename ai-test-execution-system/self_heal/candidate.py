"""Repair Candidate 的受限数据模型。"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict


@dataclass(frozen=True)
class Locator:
    using: str
    value: str

    @classmethod
    def from_dict(cls, value: Dict[str, Any]) -> "Locator":
        if set(value) != {"using", "value"}:
            raise ValueError("locator 只能包含 using 与 value。")
        if not isinstance(value["using"], str) or not isinstance(value["value"], str):
            raise ValueError("locator 的 using 与 value 必须为字符串。")
        return cls(using=value["using"], value=value["value"])


@dataclass(frozen=True)
class RepairCandidate:
    target: str
    old_locator: Locator
    candidate: Locator
    evidence: Dict[str, Any]
    provenance: Dict[str, Any]

    @classmethod
    def from_dict(cls, value: Dict[str, Any]) -> "RepairCandidate":
        required = {"target", "old_locator", "candidate", "evidence", "provenance"}
        if set(value) != required:
            raise ValueError("Repair Candidate 字段不完整或包含未允许字段。")
        if not isinstance(value["target"], str):
            raise ValueError("Repair Candidate target 必须为字符串。")
        if not isinstance(value["evidence"], dict) or not isinstance(value["provenance"], dict):
            raise ValueError("Repair Candidate evidence 与 provenance 必须为对象。")
        return cls(
            target=value["target"],
            old_locator=Locator.from_dict(value["old_locator"]),
            candidate=Locator.from_dict(value["candidate"]),
            evidence=value["evidence"],
            provenance=value["provenance"],
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def load_candidate(path: Path) -> RepairCandidate:
    return RepairCandidate.from_dict(json.loads(path.read_text(encoding="utf-8")))


def save_candidate(candidate: RepairCandidate, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(candidate.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
