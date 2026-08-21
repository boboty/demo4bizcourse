"""确定性 Policy Gate：候选只可能替换正式用例的一个 locator。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import yaml

from self_heal.candidate import RepairCandidate, load_candidate
from self_heal.dom import matching_node_count


REQUIRED_FACTS = {
    "order_status": "PAID",
    "payment_count": 1,
    "payment_record.status": "SUCCEEDED",
    "inventory.available_quantity": 9,
}


def _pay_step(case: Dict[str, Any]) -> Dict[str, Any]:
    steps = case.get("ui", {}).get("steps", [])
    found = [step for step in steps if step.get("id") == "pay_order"]
    if len(found) != 1:
        raise ValueError("正式用例必须且只能有一个 pay_order 步骤。")
    return found[0]


def review_candidate(case_path: Path, candidate: RepairCandidate, page_source: str) -> Dict[str, Any]:
    case = yaml.safe_load(case_path.read_text(encoding="utf-8"))
    reasons: list[str] = []
    try:
        pay_step = _pay_step(case)
    except ValueError as error:
        return {"decision": "REJECTED", "reasons": [str(error)]}
    current = pay_step.get("locator")
    if candidate.target != "pay_button":
        reasons.append("target 必须是 pay_button。")
    if current != {"using": candidate.old_locator.using, "value": candidate.old_locator.value}:
        reasons.append("Candidate old_locator 与正式 pay_order locator 不一致。")
    if candidate.candidate.using != "css selector":
        reasons.append("只允许 css selector locator。")
    if candidate.candidate.value == candidate.old_locator.value:
        reasons.append("Candidate 没有修复 locator。")
    if case.get("assertions", {}).get("api_facts", {}).get("equals") != REQUIRED_FACTS:
        reasons.append("固定 API 业务断言被修改或缺失。")
    if [step.get("id") for step in case.get("ui", {}).get("steps", [])] != [
        "login", "submit_login", "open_pending_order", "pay_order"
    ]:
        reasons.append("Candidate 不得删除、跳过或改变支付业务步骤。")
    try:
        matches = matching_node_count(page_source, {"using": candidate.candidate.using, "value": candidate.candidate.value})
        if matches != 1:
            reasons.append("Candidate 在当前 DOM 中匹配 {0} 个元素，必须唯一匹配。".format(matches))
    except ValueError as error:
        matches = None
        reasons.append(str(error))
    return {
        "decision": "APPROVED" if not reasons else "REJECTED",
        "reasons": reasons or ["仅替换 pay_order locator；固定业务步骤与 API 断言未变；当前 DOM 唯一匹配。"],
        "target": candidate.target,
        "old_locator": {"using": candidate.old_locator.using, "value": candidate.old_locator.value},
        "candidate_locator": {"using": candidate.candidate.using, "value": candidate.candidate.value},
        "unique_match_count": matches,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    }


def save_review(review: Dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("page_source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    review = review_candidate(args.case, load_candidate(args.candidate), args.page_source.read_text(encoding="utf-8"))
    save_review(review, args.output)
    print(json.dumps(review, ensure_ascii=False, indent=2))
    return 0 if review["decision"] == "APPROVED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
