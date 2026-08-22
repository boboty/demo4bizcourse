"""Round 5 的最小 Stability / Flaky History 规则。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


MINIMUM_SAMPLES = 5
STABLE = "STABLE"
FLAKY = "FLAKY"
INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"


def append_history(path: Path, record: Dict[str, Any]) -> None:
    """追加一条 JSONL 历史；不重试、不修改既有记录。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as history_file:
        history_file.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def read_history(path: Path) -> List[Dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def classify_stability(results: Iterable[str], minimum_samples: int = MINIMUM_SAMPLES) -> str:
    values = list(results)
    if len(values) < minimum_samples:
        return INSUFFICIENT_HISTORY
    outcomes = set(values)
    if outcomes == {"PASS", "FAIL"}:
        return FLAKY
    if outcomes in ({"PASS"}, {"FAIL"}):
        return STABLE
    return INSUFFICIENT_HISTORY


def summarize_history(path: Path, minimum_samples: int = MINIMUM_SAMPLES) -> Dict[str, Any]:
    records = read_history(path)
    results = [record.get("result") for record in records]
    return {
        "history_path": str(path),
        "sample_count": len(records),
        "pass_count": sum(result == "PASS" for result in results),
        "fail_count": sum(result == "FAIL" for result in results),
        "stability": classify_stability(results, minimum_samples=minimum_samples),
        "minimum_samples": minimum_samples,
    }
