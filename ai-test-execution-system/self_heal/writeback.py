"""通过验证后才可对正式 YAML 做单行、可审查的 locator 写回。"""

from __future__ import annotations

import difflib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from self_heal.candidate import RepairCandidate


def _locator_line(locator: Dict[str, str]) -> str:
    return '      locator: {{using: {0}, value: "{1}"}}'.format(locator["using"], locator["value"])


def write_back(case_path: Path, candidate: RepairCandidate, review: Dict[str, Any], verification: Dict[str, Any], audit_path: Path) -> Dict[str, Any]:
    """仅替换 pay_order 的 locator 行，前提是 Gate 和三次验证均通过。"""
    if review.get("decision") != "APPROVED":
        raise ValueError("Review 未 APPROVED，禁止写回。")
    runs = verification.get("runs", [])
    if len(runs) < 3 or not all(run.get("result") == "PASS" for run in runs):
        raise ValueError("Candidate 未完成至少三次全部 PASS 的验证，禁止写回。")
    before = case_path.read_text(encoding="utf-8")
    old_locator = {"using": candidate.old_locator.using, "value": candidate.old_locator.value}
    new_locator = {"using": candidate.candidate.using, "value": candidate.candidate.value}
    old_line = _locator_line(old_locator)
    new_line = _locator_line(new_locator)
    pay_step = re.compile(r"(    - id: pay_order\n      action: click\n)(      locator: \{using: [^\n]+\})")
    match = pay_step.search(before)
    if not match or match.group(2) != old_line:
        raise ValueError("正式用例 pay_order locator 不符合已审查的 old_locator，禁止写回。")
    after = before[: match.start(2)] + new_line + before[match.end(2) :]
    if before.count(old_line) != 1 or after.count(new_line) != 1:
        raise ValueError("写回必须且只能变更一个 locator。")
    case_path.write_text(after, encoding="utf-8")
    diff = "".join(difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile="before/cases/pay_order.yaml", tofile="after/cases/pay_order.yaml"))
    audit = {
        "written_at": datetime.now(timezone.utc).isoformat(),
        "reason": "UI V2 中旧支付 locator 真实失败；Candidate 经 Review 与三次真机验证通过。",
        "target": "pay_order.locator",
        "before": old_locator,
        "after": new_locator,
        "diff": diff,
    }
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return audit


def restore_baseline_locator(case_path: Path) -> bool:
    """恢复课堂复现用的旧 locator；不改动用例其他语义和断言。"""
    current = case_path.read_text(encoding="utf-8")
    v1 = _locator_line({"using": "css selector", "value": "#pay-now"})
    v2 = _locator_line({"using": "css selector", "value": "[data-testid='confirm-payment']"})
    if current.count(v1) == 1:
        return False
    if current.count(v2) != 1:
        raise ValueError("无法安全恢复：pay_order locator 不是本课程允许的 V2 locator。")
    case_path.write_text(current.replace(v2, v1, 1), encoding="utf-8")
    return True
