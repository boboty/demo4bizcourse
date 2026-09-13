#!/usr/bin/env python3
"""D3 独立验收：从 workspaces/demo3-validator 的业务事实源独立算出期望结果，
再通过 bin/actual-output 这一个黑盒 HTTP 入口取得系统实际输出并比较。

这是课堂里"新开 Validator Codex 会话，执行 validation/independent-validation.md"
这条人工流程的脚本化版本，用于讲师预跑、回归和 acceptance_check；不替代课堂现场
真正让一个独立 Agent 会话完成同一件事。两者读的是同一份业务事实源
（rules/export_eligibility_source_of_truth.md、rules/tenant_access_source_of_truth.md、
validation/known_applications.json、validation/cases.json），互为交叉验证。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VALIDATOR_DIR = REPO_ROOT / "workspaces" / "demo3-validator"

# 独立解释自 rules/export_eligibility_source_of_truth.md：只有这两个状态允许放款导出。
EXPORT_ELIGIBLE_STATUSES = {"APPROVED", "FUNDED"}

# 独立解释自 rules/tenant_access_source_of_truth.md：用户可见的 tenant 范围。
USER_TENANTS = {
    "alice": {"NORTH"},
    "bob": {"SOUTH"},
    "admin": {"NORTH", "SOUTH"},
}


def independent_expectation(case: dict, records: list[dict]) -> dict:
    allowed = USER_TENANTS.get(case["user"], set())
    rows = [row for row in records if row["tenant"] in allowed]

    customer_name = case["query"].get("customer_name")
    if customer_name:
        needle = customer_name.lower()
        rows = [row for row in rows if needle in row["customer_name"].lower()]

    status = case["query"].get("status")
    if status:
        rows = [row for row in rows if row["status"] == status]

    expected_list_ids = sorted(row["id"] for row in rows)
    expected_export_ids = sorted(row["id"] for row in rows if row["status"] in EXPORT_ELIGIBLE_STATUSES)
    return {"list_ids": expected_list_ids, "export_ids": expected_export_ids}


def run_actual_output(validator_dir: Path, cases_path: Path, base_url: str) -> list[dict]:
    python = REPO_ROOT / ".venv" / "bin" / "python"
    result = subprocess.run(
        [str(python), str(validator_dir / "bin" / "actual-output"), str(cases_path), base_url],
        cwd=validator_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"bin/actual-output failed: {result.stderr.strip()}")
    return json.loads(result.stdout)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8030")
    parser.add_argument("--validator-dir", default=str(VALIDATOR_DIR))
    args = parser.parse_args()

    validator_dir = Path(args.validator_dir)
    cases = json.loads((validator_dir / "validation" / "cases.json").read_text(encoding="utf-8"))
    records = json.loads((validator_dir / "validation" / "known_applications.json").read_text(encoding="utf-8"))

    try:
        actual = run_actual_output(validator_dir, validator_dir / "validation" / "cases.json", args.base_url)
    except RuntimeError as exc:
        print(f"BLOCKER: {exc}", file=sys.stderr)
        return 2
    actual_by_id = {item["id"]: item for item in actual}

    print("Golden validation:")
    overall_pass = True
    rows_out = []
    for case in cases:
        expected = independent_expectation(case, records)
        got = actual_by_id.get(case["id"], {})
        list_ok = got.get("list_ids") == expected["list_ids"]
        export_ok = got.get("export_ids") == expected["export_ids"]
        case_pass = list_ok and export_ok
        overall_pass = overall_pass and case_pass

        detail = ""
        if not list_ok:
            detail += f" list expected {len(expected['list_ids'])} ids={expected['list_ids']}, actual {len(got.get('list_ids', []))} ids={got.get('list_ids')}"
        if not export_ok:
            detail += f" export expected {len(expected['export_ids'])} ids={expected['export_ids']}, actual {len(got.get('export_ids', []))} ids={got.get('export_ids')}"

        label = f"{case['id']} {case['label']}"
        status_word = "PASS" if case_pass else "FAIL"
        print(f"{label:<20}{status_word:<6}{detail}")
        rows_out.append({"id": case["id"], "label": case["label"], "pass": case_pass, "detail": detail.strip()})

    print()
    print("Overall:", "PASS" if overall_pass else "BLOCKER")
    return 0 if overall_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
