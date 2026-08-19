"""独立地将测试源代码与原始验收标准对照，不执行 pytest。"""

import argparse
import re
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REQUIREMENT = PROJECT_ROOT / "business" / "requirement.md"
ACCEPTANCE = PROJECT_ROOT / "business" / "acceptance.md"
TEST_FILES = {
    "generated": PROJECT_ROOT / "tests" / "generated" / "test_orders.py",
    "verified": PROJECT_ROOT / "tests" / "verified" / "test_orders.py",
}
REPORTS = {
    "generated": PROJECT_ROOT / "evidence" / "independent-review-report.md",
    "verified": PROJECT_ROOT / "evidence" / "final-test-report.md",
}


@dataclass(frozen=True)
class ReviewResult:
    target: str
    accepted: bool
    missing: list[str]
    execution_status: str


def _has_all(source: str, required: tuple[str, ...]) -> bool:
    return all(item in source for item in required)


def _has_scenario_evidence(source: str, scenario: str, required: tuple[str, ...]) -> bool:
    """要求关键断言出现在同一个测试函数中，避免不同测试的零散断言被误合并。"""

    test_functions = re.split(r"(?m)^def ", source)[1:]
    return any(scenario in case and _has_all(case, required) for case in test_functions)


def review(target: str) -> ReviewResult:
    """检查 AC 声明加上真正的业务断言；不将 pytest 绿灯当作验收。"""

    # 显式读取全部独立输入，保证验收源是原始需求而不是测试作者的解释。
    requirement = REQUIREMENT.read_text(encoding="utf-8")
    acceptance = ACCEPTANCE.read_text(encoding="utf-8")
    source = TEST_FILES[target].read_text(encoding="utf-8")
    if "GOLD" not in requirement or "AC-004" not in acceptance:
        raise RuntimeError("Independent review inputs are incomplete.")

    declared_coverage = set(re.findall(r"AC-\d{3}", "\n".join(
        line for line in source.splitlines() if "covers:" in line.lower()
    )))
    checks = {
        "AC-001": ('status_code == 200',),
        "AC-002": ('membershipDiscount"] == 100',),
        "AC-003": ('couponDiscount"] == 100',),
    }
    missing = [
        ac for ac, evidence in checks.items()
        if ac not in declared_coverage or not _has_all(source, evidence)
    ]
    # AC-004/005 的关键断言不能散落在不同测试里，必须针对同一组合场景形成证据链。
    ac4_evidence = (
        'membershipDiscount"] == 100',
        'couponDiscount"] == 100',
        'discount"] == 200',
        '"CHECK_GOLD_LEVEL" in payload["decisionTrace"]',
        '"APPLY_GOLD_DISCOUNT" in payload["decisionTrace"]',
    )
    ac5_evidence = (
        'membershipDiscount"] == 100',
        'couponDiscount"] == 0',
        '"RETAIN_GOLD_DISCOUNT" in payload["decisionTrace"]',
    )
    if "AC-004" not in declared_coverage or not _has_scenario_evidence(source, '"coupon": "VIP100"', ac4_evidence):
        missing.append("AC-004")
    if "AC-005" not in declared_coverage or not _has_scenario_evidence(source, '"coupon": "VIP100-NO-STACK"', ac5_evidence):
        missing.append("AC-005")
    execution_report = (
        PROJECT_ROOT / "evidence" / "generated-test-report.md"
        if target == "generated"
        else PROJECT_ROOT / "evidence" / "final-test-report.md"
    )
    execution_status = "PASS" if execution_report.exists() and "pytest: PASS" in execution_report.read_text(encoding="utf-8") else "NOT RECORDED"
    return ReviewResult(target, not missing, missing, execution_status)


def write_report(result: ReviewResult) -> Path:
    report = REPORTS[result.target]
    result_text = "PASS" if result.accepted else "REJECTED"
    missing_lines = "\n".join(
        f"- {ac} - 关键业务规则缺少有效测试证据" for ac in result.missing
    ) or "- None"
    # verified 的最终报告同时保留 pytest 执行结论，便于之后单独复查仍能看到完整闭环。
    execution_line = f"- pytest: {result.execution_status}\n" if result.target == "verified" else ""
    report.write_text(
        "# 独立验收报告\n\n"
        f"- Review target: `tests/{result.target}/test_orders.py`\n"
        "- Inputs: `business/requirement.md`, `business/acceptance.md`, test source\n"
        f"{execution_line}"
        f"- Test execution evidence: {result.execution_status}\n"
        f"- RESULT: {result_text}\n\n"
        "## Missing evidence\n\n"
        f"{missing_lines}\n\n"
        "独立验收检查覆盖声明和必要的业务断言；它没有重新运行 pytest。\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Review generated or verified tests against acceptance evidence.")
    parser.add_argument("--target", choices=TEST_FILES, default="generated")
    args = parser.parse_args()
    result = review(args.target)
    report = write_report(result)
    review_status = "PASS" if result.accepted else "REJECTED"
    print("INDEPENDENT BUSINESS REVIEW")
    print(f"TEST EXECUTION : {result.execution_status}")
    print(f"INDEPENDENT REVIEW : {review_status}")
    if result.missing:
        print("Missing:")
        for ac in result.missing:
            print(f"{ac} - 关键业务规则缺少有效测试证据")
    print(f"Evidence: {report.relative_to(PROJECT_ROOT)}")
    # REJECTED 是这一步的预期教学结果，故返回 0，以便讲师可连续演示。
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
