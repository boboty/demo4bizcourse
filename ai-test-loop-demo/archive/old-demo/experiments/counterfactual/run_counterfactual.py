"""反证实验：一键把 app/service.py 换成 service_buggy.py、跑两套测试套件、再一键还原。

不改动仓库主干文件的持久状态——app/service.py 全程通过内存备份 + finally 还原，
任何一次运行结束（哪怕 pytest 内部抛异常）都会把原文件写回去。

产出写到 demo-evidence/page30/counterfactual/：
  - service.diff                 真实实现 vs 错误实现的 diff
  - generated-suite-output.txt   错误实现下 tests/generated 的 pytest 输出
  - verified-suite-output.txt    错误实现下 tests/verified 的 pytest 输出
"""

import difflib
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REAL_SERVICE = PROJECT_ROOT / "app" / "service.py"
BUGGY_SERVICE = PROJECT_ROOT / "experiments" / "counterfactual" / "service_buggy.py"
OUT_DIR = PROJECT_ROOT / "demo-evidence" / "page30" / "counterfactual"


def run_pytest(target: str) -> tuple[int, str]:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", target, "-v"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.returncode, result.stdout + result.stderr


def main() -> int:
    original = REAL_SERVICE.read_text(encoding="utf-8")
    buggy = BUGGY_SERVICE.read_text(encoding="utf-8")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    diff = "".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            buggy.splitlines(keepends=True),
            fromfile="app/service.py (real)",
            tofile="experiments/counterfactual/service_buggy.py (injected bug)",
        )
    )
    (OUT_DIR / "service.diff").write_text(diff, encoding="utf-8")

    try:
        REAL_SERVICE.write_text(buggy, encoding="utf-8")
        gen_code, gen_output = run_pytest("tests/generated")
        ver_code, ver_output = run_pytest("tests/verified")
    finally:
        REAL_SERVICE.write_text(original, encoding="utf-8")
        restored_ok = REAL_SERVICE.read_text(encoding="utf-8") == original

    def desensitize(text: str) -> str:
        # rootdir 会把本机真实用户路径印进 pytest 输出；换成课堂用的通用占位路径。
        return text.replace(str(PROJECT_ROOT), "/workspace/ai-test-loop-demo")

    (OUT_DIR / "generated-suite-output.txt").write_text(
        desensitize(f"$ python -m pytest tests/generated -v   # 运行时 app/service.py 已被替换为错误实现\n\n{gen_output}"),
        encoding="utf-8",
    )
    (OUT_DIR / "verified-suite-output.txt").write_text(
        desensitize(f"$ python -m pytest tests/verified -v   # 运行时 app/service.py 已被替换为错误实现\n\n{ver_output}"),
        encoding="utf-8",
    )

    print("COUNTERFACTUAL EXPERIMENT")
    print(f"app/service.py restored to original: {'OK' if restored_ok else 'FAILED — MANUAL CHECK NEEDED'}")
    print(f"generated suite under buggy impl : exit={gen_code} ({'ALL GREEN' if gen_code == 0 else 'HAS FAILURES'})")
    print(f"verified  suite under buggy impl : exit={ver_code} ({'ALL GREEN' if ver_code == 0 else 'HAS FAILURES'})")
    print(f"Evidence written to: {OUT_DIR.relative_to(PROJECT_ROOT)}")
    return 0 if restored_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
