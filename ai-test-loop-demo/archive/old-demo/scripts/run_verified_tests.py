"""执行修复后的测试并在同一闭环中触发独立验收。"""

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT = PROJECT_ROOT / "evidence" / "final-test-report.md"


def run_verified_tests() -> int:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/verified"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    output = (result.stdout + result.stderr).strip()
    status = "PASS" if result.returncode == 0 else "FAILED"
    REPORT.write_text(
        "# 最终验证测试执行报告\n\n"
        f"- UTC: {datetime.now(timezone.utc).isoformat()}\n"
        "- Test asset: `tests/verified/test_orders.py`\n"
        f"- pytest: {status}\n\n```text\n{output}\n```\n",
        encoding="utf-8",
    )
    print("VERIFIED TEST EXECUTION")
    print(output)
    print(f"pytest: {status}")
    if result.returncode != 0:
        return result.returncode

    review = subprocess.run(
        [sys.executable, "scripts/run_independent_review.py", "--target", "verified"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    print(review.stdout.strip())
    if review.stderr:
        print(review.stderr.strip(), file=sys.stderr)
    if review.returncode != 0 or "INDEPENDENT REVIEW : PASS" not in review.stdout:
        print("FINAL INDEPENDENT REVIEW FAILED")
        return 1
    print("ALL VERIFIED TESTS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_verified_tests())
