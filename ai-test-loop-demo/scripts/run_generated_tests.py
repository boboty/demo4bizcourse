"""执行模拟 AI 第一次生成的测试，并记录执行证据。"""

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT = PROJECT_ROOT / "evidence" / "generated-test-report.md"


def run_generated_tests() -> int:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/generated"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    output = (result.stdout + result.stderr).strip()
    status = "PASS" if result.returncode == 0 else "FAILED"
    REPORT.write_text(
        "# AI 第一次生成测试执行报告\n\n"
        f"- UTC: {datetime.now(timezone.utc).isoformat()}\n"
        "- Test asset: `tests/generated/test_orders.py`\n"
        f"- pytest: {status}\n\n"
        "```text\n"
        f"{output}\n"
        "```\n",
        encoding="utf-8",
    )
    print("AI GENERATED TEST EXECUTION")
    print(output)
    print(f"pytest: {status}")
    if result.returncode == 0:
        print("ALL TESTS PASSED")
    else:
        print("TEST EXECUTION FAILED")
    print(f"Evidence: {REPORT.relative_to(PROJECT_ROOT)}")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(run_generated_tests())

