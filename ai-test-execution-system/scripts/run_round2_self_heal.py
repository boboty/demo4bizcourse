#!/usr/bin/env python3
"""Round 2 only: V2 真实 locator failure → AI Candidate → Gate → Verify → Write Back。"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_pay_order_ios import (  # noqa: E402
    WebDriver,
    appium_capabilities,
    assert_equals,
    execute_ui,
    lan_ip,
    read_case,
    require_ok,
    run_once,
    start_appium,
    stop_appium,
)
from self_heal.analyzer import generate_candidate, import_interactive_candidate  # noqa: E402
from self_heal.candidate import RepairCandidate  # noqa: E402
from self_heal.dom import matching_node_count  # noqa: E402
from self_heal.reviewer import review_candidate, save_review  # noqa: E402
from self_heal.writeback import write_back  # noqa: E402


V2_CONFIGURATION = {"ui_version": "v2", "payment_mode": "normal", "product_bug_mode": "off"}
REQUIRED_FACTS = {
    "order_status": "PAID",
    "payment_count": 1,
    "payment_record.status": "SUCCEEDED",
    "inventory.available_quantity": 9,
}


def new_evidence_dir() -> Path:
    path = PROJECT_ROOT / "evidence" / ("round2-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    path.mkdir(parents=True, exist_ok=False)
    return path


def save_json(path: Path, value: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def require_old_locator(case: Dict[str, Any]) -> None:
    locator = case["ui"]["steps"][-1]["locator"]
    if locator != {"using": "css selector", "value": "#pay-now"}:
        raise RuntimeError("Round 2 首次失败必须从正式旧 locator #pay-now 开始；请先运行 restore_self_heal_baseline.sh。")


def set_v2_and_prepare(case: Dict[str, Any], base_url: str) -> str:
    require_ok(base_url + case["test_data"]["reset_endpoint"], "POST")
    require_ok(base_url + "/api/config", "PUT", V2_CONFIGURATION)
    config = require_ok(base_url + "/api/config")
    assert_equals(config, V2_CONFIGURATION, "Round 2 V2 配置")
    prepared = require_ok(base_url + case["test_data"]["prepare_pending_order_endpoint"], "POST")
    order_id = prepared.get(case["test_data"]["order_id_response_field"])
    if not order_id or prepared.get("order_status") != "PENDING_PAY":
        raise AssertionError("Round 2 prepare 未返回 PENDING_PAY order_id。")
    return str(order_id)


def classify_locator_failure(
    failure_step: str, old_locator: Dict[str, str], page_source: str
) -> Dict[str, Any]:
    """只有 pay_order 且真实 DOM 中旧 locator 匹配 0 才允许进入 Self-Heal。"""
    match_count = matching_node_count(page_source, old_locator)
    result = "EXPECTED_LOCATOR_FAILURE" if failure_step == "pay_order" and match_count == 0 else "EXECUTION_FAILURE"
    return {"result": result, "old_locator_match_count": match_count}


def capture_old_locator_failure(case: Dict[str, Any], base_url: str, evidence_dir: Path, label: str) -> Dict[str, Any]:
    """在 V2 页面执行未改动的正式资产，并且只能接受 pay_order 元素定位失败。"""
    failure_dir = evidence_dir / label
    failure_dir.mkdir(parents=True, exist_ok=False)
    order_id = set_v2_and_prepare(case, base_url)
    record: Dict[str, Any] = {
        "failure_step": "start",
        "old_locator": case["ui"]["steps"][-1]["locator"],
        "target_semantic": "支付当前待付款订单",
        "result": "UNEXPECTED_PASS",
    }
    driver = WebDriver()
    appium = None
    try:
        appium = start_appium(failure_dir / case["evidence"]["appium_log"])
        execute_ui(driver, case, base_url, record)
        raise AssertionError("UI V2 仍接受旧 locator；没有制造真实 locator failure。")
    except Exception as error:
        record["error"] = str(error)
        record["failure_step"] = record.get("current_step", "unknown")
        if not driver.session_id:
            raise RuntimeError("未建立真机 session，不能生成 UI locator failure evidence。") from error
        try:
            page_source = driver.page_source()
            (failure_dir / "page-source.html").write_text(page_source, encoding="utf-8")
            (failure_dir / "failure-screenshot.png").write_bytes(driver.screenshot())
            classification = classify_locator_failure(
                record["failure_step"], record["old_locator"], page_source
            )
            record.update(classification)
        except Exception as evidence_error:
            record["result"] = "EXECUTION_FAILURE"
            record["evidence_error"] = str(evidence_error)
            save_json(failure_dir / "failure-context.json", record)
            raise RuntimeError("无法取得真实 page source 或完成旧 locator DOM 检查。") from evidence_error
        facts_endpoint = case["assertions"]["api_facts"]["endpoint"].format(order_id=order_id)
        record["api_facts"] = require_ok(base_url + facts_endpoint)
        if record["result"] != "EXPECTED_LOCATOR_FAILURE":
            save_json(failure_dir / "failure-context.json", record)
            raise RuntimeError(
                "失败不能作为 Self-Heal 输入：failure_step={0}, old_locator_match_count={1}".format(
                    record["failure_step"], record["old_locator_match_count"]
                )
            ) from error
    finally:
        try:
            driver.quit()
        finally:
            stop_appium(appium)
        # failure 也要清理，避免污染临时 Candidate 验证。
        require_ok(base_url + case["cleanup"]["endpoint"], "POST")
    save_json(failure_dir / "failure-context.json", record)
    return {"directory": failure_dir, "record": record}


def temporary_case(case: Dict[str, Any], candidate: RepairCandidate) -> Dict[str, Any]:
    result = copy.deepcopy(case)
    result["ui"]["steps"][-1]["locator"] = {
        "using": candidate.candidate.using,
        "value": candidate.candidate.value,
    }
    # Case 的 V1 声明属于 Round 1 资产；Round 2 的目标版本由执行时配置指定。
    return result


def verify_candidate(case: Dict[str, Any], candidate: RepairCandidate, base_url: str, evidence_dir: Path, runs: int = 3) -> Dict[str, Any]:
    candidate_case = temporary_case(case, candidate)
    results = []
    for index in range(1, runs + 1):
        record = run_once(
            candidate_case,
            base_url,
            evidence_dir / "candidate-verification" / "run-{0:03d}".format(index),
            configuration_override=V2_CONFIGURATION,
            round_name="Round 2 Candidate Verify",
        )
        # run_once 已使用原案例的固定 API assertions；这里显式记录，避免只用 UI PASS。
        results.append({
            "run": index,
            "result": record["result"],
            "ui_assertion": record.get("ui_assertion"),
            "api_assertion": record.get("api_assertion"),
            "cleanup": record.get("cleanup"),
        })
    summary = {"runs": results, "all_pass": all(item["result"] == "PASS" for item in results)}
    save_json(evidence_dir / "candidate-verification.json", summary)
    return summary


def write_pass_summary(path: Path, candidate: RepairCandidate, verification: Dict[str, Any]) -> None:
    lines = [
        "# Round 2 PASS 摘要（脱敏）",
        "",
        "- physical iPhone: true",
        "- UI V1 baseline: PASS",
        "- UI V2 old locator `#pay-now`: expected failure at `pay_order`",
        "- AI Candidate: {0}".format(candidate.provenance["kind"]),
        "- Review / Policy Gate: APPROVED",
        "- Candidate unique DOM match: 1",
        "- Candidate verification: {0}/3 PASS".format(len(verification["runs"])),
        "- Fixed API facts: PAID / payment_count=1 / SUCCEEDED / inventory=9",
        "- Write Back: only `pay_order.locator` changed",
        "- Post-writeback V2 deterministic rerun without AI: PASS",
        "- Baseline restore and repeat old-locator failure: PASS",
        "",
        "Raw screenshots, DOM, Appium logs, model request/response identifiers and device data remain local and are ignored by Git.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, default=PROJECT_ROOT / "cases" / "pay_order.yaml")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--interactive-candidate", type=Path, help="从本次真实失败上下文生成并导入的交互式 Codex Candidate JSON。")
    parser.add_argument("--stop-after-failure", action="store_true", help="只完成 V1 baseline 和 V2 真实失败，供交互式 Codex 读取 evidence 后再继续。")
    parser.add_argument("--failure-dir", type=Path, help="从 --stop-after-failure 生成的 v2-old-locator-failure 目录继续。")
    args = parser.parse_args()
    if args.stop_after_failure and args.failure_dir:
        parser.error("--stop-after-failure 与 --failure-dir 不能同时使用。")
    if args.failure_dir and not args.interactive_candidate:
        parser.error("--failure-dir 只用于导入交互式 Codex Candidate 后继续。")
    case = read_case(args.case)
    require_old_locator(case)
    base_url = (args.base_url or "http://{0}:8000".format(lan_ip())).rstrip("/")
    evidence_dir = new_evidence_dir()
    outcome: Dict[str, Any] = {"round": "Round 2", "result": "FAIL"}
    try:
        if args.failure_dir:
            failure_dir = args.failure_dir.resolve()
            required = [failure_dir / name for name in ("failure-context.json", "page-source.html", "failure-screenshot.png")]
            if not all(path.is_file() for path in required):
                raise RuntimeError("--failure-dir 不是完整的真实 failure bundle。")
            baseline_record = failure_dir.parent / "baseline-v1" / "run.json"
            if not baseline_record.is_file() or json.loads(baseline_record.read_text(encoding="utf-8")).get("result") != "PASS":
                raise RuntimeError("failure bundle 缺少同次真实 V1 baseline PASS 证据，禁止继续。")
            outcome["baseline_v1"] = "PASS（从 failure bundle 复核）"
            outcome["old_locator_failure"] = "EXPECTED_LOCATOR_FAILURE（从 failure bundle 复核）"
        else:
            # 1. 已有 Round 1 正式资产在 V1 的真实 baseline。
            baseline = run_once(case, base_url, evidence_dir / "baseline-v1", round_name="Round 2 baseline V1")
            if baseline["result"] != "PASS":
                raise RuntimeError("Round 1 baseline V1 未 PASS。")
            outcome["baseline_v1"] = "PASS"

            # 2. V2 下保持正式旧 locator，收集真实失败 bundle。
            failure = capture_old_locator_failure(case, base_url, evidence_dir, "v2-old-locator-failure")
            outcome["old_locator_failure"] = failure["record"]["result"]
            failure_dir = failure["directory"]
            if args.stop_after_failure:
                outcome["result"] = "STOPPED_AFTER_REAL_FAILURE"
                save_json(evidence_dir / "round2-outcome.json", outcome)
                print("真实 failure bundle 已保存：{0}".format(failure_dir))
                print("下一步：python3 scripts/render_round2_candidate_prompt.py {0}/failure-context.json {0}/page-source.html {0}/failure-screenshot.png".format(failure_dir))
                print("将交互式 Codex 的真实 JSON 输出保存到本机后，继续：")
                print("python3 scripts/run_round2_self_heal.py --failure-dir {0} --interactive-candidate /path/to/real-interactive-candidate.json".format(failure_dir))
                return 0

        # 3. 真实模型只在这一处生成候选；API Key 缺失即终止，没有 fallback。
        candidate_path = PROJECT_ROOT / "self_heal" / "candidates" / "round2-candidate.json"
        if args.interactive_candidate:
            candidate = import_interactive_candidate(args.interactive_candidate, failure_dir / "failure-context.json", candidate_path)
        else:
            candidate = generate_candidate(
                failure_dir / "failure-context.json",
                failure_dir / "page-source.html",
                failure_dir / "failure-screenshot.png",
                candidate_path,
            )
        outcome["ai_candidate"] = "GENERATED"

        # 4. Policy Gate 不会改动案例。
        review = review_candidate(args.case, candidate, (failure_dir / "page-source.html").read_text(encoding="utf-8"))
        save_review(review, evidence_dir / "review.json")
        if review["decision"] != "APPROVED":
            raise RuntimeError("Review / Policy Gate REJECTED：{0}".format("; ".join(review["reasons"])))
        outcome["review"] = "APPROVED"

        # 5. 临时内存案例的三次真实验证；正式 YAML 此时仍为 #pay-now。
        verification = verify_candidate(case, candidate, base_url, evidence_dir, runs=3)
        if not verification["all_pass"]:
            raise RuntimeError("Candidate 三次真实验证未全部 PASS。")
        outcome["candidate_verification"] = "3/3 PASS"

        # 6. 仅在 Gate + Verify 成功后，单行写回，并以正式资产执行一次 V2（不调用 AI）。
        audit = write_back(args.case, candidate, review, verification, evidence_dir / "writeback-audit.json")
        outcome["writeback"] = audit["after"]
        written_case = read_case_after_writeback(args.case)
        rerun = run_once(
            written_case,
            base_url,
            evidence_dir / "post-writeback-v2",
            configuration_override=V2_CONFIGURATION,
            round_name="Round 2 post-writeback V2",
        )
        if rerun["result"] != "PASS":
            raise RuntimeError("写回后的正式资产 V2 rerun 未 PASS。")
        outcome["post_writeback_rerun"] = "PASS"

        # 7. 执行恢复脚本的同等逻辑，并再次用真机制造旧 locator failure。
        from scripts.restore_self_heal_baseline import main as restore_main

        restore_main()
        restored_case = read_case(args.case)
        require_old_locator(restored_case)
        repeat_failure = capture_old_locator_failure(restored_case, base_url, new_evidence_dir(), "repeat-v2-old-locator-failure")
        if repeat_failure["record"]["result"] != "EXPECTED_LOCATOR_FAILURE":
            raise RuntimeError("baseline restore 后未能再次制造旧 locator failure。")
        require_ok(base_url + restored_case["cleanup"]["endpoint"], "POST")
        outcome["baseline_restore"] = "PASS"
        outcome["result"] = "PASS"
        write_pass_summary(PROJECT_ROOT / "evidence" / "round2-pass-summary.md", candidate, verification)
    except Exception as error:
        outcome["error"] = str(error)
        save_json(evidence_dir / "round2-outcome.json", outcome)
        print(json.dumps(outcome, ensure_ascii=False, indent=2))
        return 1
    save_json(evidence_dir / "round2-outcome.json", outcome)
    print(json.dumps(outcome, ensure_ascii=False, indent=2))
    return 0


def read_case_after_writeback(case_path: Path) -> Dict[str, Any]:
    """写回后的 V2 locator 仍是物理 iOS 案例；Round 1 的 V1 限制不应阻断检查。"""
    import yaml

    case = yaml.safe_load(case_path.read_text(encoding="utf-8"))
    if case.get("device", {}).get("physical") is not True:
        raise RuntimeError("写回后的正式资产必须保持 physical iPhone。")
    if case["ui"]["steps"][-1]["locator"] != {"using": "css selector", "value": "[data-testid='confirm-payment']"}:
        raise RuntimeError("写回后的 locator 不是已验证的 V2 Candidate。")
    if case["assertions"]["api_facts"]["equals"] != REQUIRED_FACTS:
        raise RuntimeError("写回不允许改变固定 API assertions。")
    return case


if __name__ == "__main__":
    raise SystemExit(main())
