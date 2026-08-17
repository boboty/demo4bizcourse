"""独立执行某一次盲测生成的测试文件，不采信生成者自己的执行结论。

用法：python experiments/real-generation/run_trial.py trial-1
"""

import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASE_DIR = PROJECT_ROOT / "experiments" / "real-generation"


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: run_trial.py <trial-dir-name>", file=sys.stderr)
        return 2
    trial_dir = BASE_DIR / sys.argv[1]
    test_file = trial_dir / "generated_test_orders.py"
    if not test_file.is_file():
        print(f"no generated test file at {test_file}", file=sys.stderr)
        return 2

    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_file), "-v"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    output = result.stdout + result.stderr
    (trial_dir / "pytest-run-output.txt").write_text(
        f"$ python -m pytest {test_file.relative_to(PROJECT_ROOT)} -v\n\n{output}",
        encoding="utf-8",
    )
    print(output)
    print(f"exit={result.returncode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
