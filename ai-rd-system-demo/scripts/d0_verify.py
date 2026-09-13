#!/usr/bin/env python3
"""不调用模型的 D0 reset、起点状态、目标状态与隔离预检。

D0 课堂只使用开发侧可见的 pytest 反馈；本脚本属于讲师课前 QA，
其中的参考实现只用于证明目标状态可达成，不进入课堂 workspace。
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "instructor/baselines/d0-first-loop"
WORKSPACE = ROOT / "workspaces/d0-first-loop"
REFERENCE = ROOT / "instructor/reference/d0_repayment_service.py"
D0_TESTS = "tests/test_repayment_schedule.py"
D0_SOURCE = "app/repayment/service.py"
IGNORED = {".git", ".venv", "__pycache__", ".pytest_cache"}
problems: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    print(("PASS" if condition else "BLOCKER"), name, detail)
    if not condition:
        problems.append(name)


def files(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and not IGNORED.intersection(path.parts)
    }


def tree_digest(root: Path) -> str:
    payload = [(name, hashlib.sha256(data).hexdigest()) for name, data in sorted(files(root).items())]
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode()).hexdigest()


def pytest(root: Path, target: str | None = None) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, "-m", "pytest", "-q"]
    if target:
        command.append(target)
    return subprocess.run(command, cwd=root, text=True, capture_output=True, check=False)


def last_line(result: subprocess.CompletedProcess[str]) -> str:
    lines = result.stdout.strip().splitlines() or result.stderr.strip().splitlines()
    return lines[-1] if lines else "无输出"


def main() -> int:
    expected_python = ROOT / ".venv" / "bin" / "python"
    check(
        "Python 3.12 root venv",
        sys.version_info[:2] == (3, 12) and Path(sys.executable) == expected_python,
        f"{sys.executable} / Python {sys.version_info.major}.{sys.version_info.minor}",
    )
    check("D0 baseline exists", BASELINE.is_dir())
    check("D0 reference implementation exists", REFERENCE.is_file())
    check(
        "D0 workspace isolation rule",
        (BASELINE / "AGENTS.md").is_file()
        and "当前目录就是本次 D0 的完整项目上下文" in (BASELINE / "AGENTS.md").read_text(encoding="utf-8")
        and "不读取父目录或兄弟 workspace" in (BASELINE / "AGENTS.md").read_text(encoding="utf-8"),
    )

    reset = subprocess.run([str(ROOT / "scripts/reset_d0.sh")], cwd=ROOT, text=True, capture_output=True, check=False)
    check("reset_d0 succeeds", reset.returncode == 0, reset.stderr.strip())
    check(
        "reset_d0 restores the frozen D0 baseline",
        tree_digest(WORKSPACE) == tree_digest(BASELINE),
    )
    reset_again = subprocess.run([str(ROOT / "scripts/reset_d0.sh")], cwd=ROOT, text=True, capture_output=True, check=False)
    check(
        "reset_d0 is repeatable and lands on the same digest",
        reset_again.returncode == 0 and tree_digest(WORKSPACE) == tree_digest(BASELINE),
    )

    existing = pytest(WORKSPACE, "tests/test_financing_baseline.py")
    check("原有融资列表测试正常", existing.returncode == 0, last_line(existing))

    first = pytest(WORKSPACE, D0_TESTS)
    second = pytest(WORKSPACE, D0_TESTS)
    d0_output = (first.stdout or "") + (first.stderr or "")
    check("D0 起点是红灯（故障条件存在）", first.returncode != 0, last_line(first))
    check("D0 起点失败可重复", second.returncode != 0 and last_line(second) == last_line(first), last_line(second))
    check(
        "D0 失败来自真实断言，而不是缺文件或语法错误",
        "AssertionError" in d0_output
        and "99999.99" in d0_output
        and "DID NOT RAISE" in d0_output
        and "ModuleNotFoundError" not in d0_output
        and "SyntaxError" not in d0_output,
    )
    baseline_source = (BASELINE / D0_SOURCE).read_text(encoding="utf-8")
    check(
        "D0 故障点在待完成模块内，且起点与参考实现不同",
        (BASELINE / D0_SOURCE).is_file()
        and baseline_source != REFERENCE.read_text(encoding="utf-8")
        and "raise ValueError" not in baseline_source
        and D0_SOURCE in files(WORKSPACE),
    )

    with tempfile.TemporaryDirectory(prefix="d0-reference-") as temp:
        fixed = Path(temp) / "workspace"
        shutil.copytree(WORKSPACE, fixed, ignore=shutil.ignore_patterns(*IGNORED))
        shutil.copy(REFERENCE, fixed / D0_SOURCE)
        solved = pytest(fixed)
        check("修复后的目标状态可被验证（全部测试通过）", solved.returncode == 0, last_line(solved))
        check(
            "目标状态不需要修改测试",
            (fixed / D0_TESTS).read_bytes() == (BASELINE / D0_TESTS).read_bytes()
            and (fixed / "tests/test_financing_baseline.py").read_bytes()
            == (BASELINE / "tests/test_financing_baseline.py").read_bytes(),
        )

    workspace_text = "\n".join(text for _, data in files(WORKSPACE).items() for text in [data.decode("utf-8", errors="replace")])
    task = (ROOT / "instructor/d0/task.txt").read_text(encoding="utf-8").strip().splitlines()[0]
    forbidden = [task, "参考实现", "Golden", "golden", "独立验收", "fallback", "d0_repayment_service", "d1-", "demo12-", "demo3-", "demo4-"]
    leaks = [token for token in forbidden if token in workspace_text]
    check("D0 workspace 不含任务文本、课堂材料或后续讲次资产", not leaks, ", ".join(leaks))
    check(
        "D0 workspace 不含讲师侧 reference 目录",
        not (WORKSPACE / "instructor").exists() and not (WORKSPACE / "reference").exists(),
    )

    for other in ("demo12-financing", "demo3-developer", "demo3-validator", "demo4-sedimentation", "d1-level1", "d1-level2", "d1-level3"):
        other_root = ROOT / "workspaces" / other
        if not other_root.is_dir():
            continue
        other_text = "\n".join(text for _, data in files(other_root).items() for text in [data.decode("utf-8", errors="replace")])
        check(
            f"D0 未泄漏进 {other}",
            "d0-first-loop" not in other_text and "repayment" not in other_text.lower(),
        )

    fallback = ROOT / "instructor/d0/fallback"
    if fallback.is_dir():
        metadata = json.loads((fallback / "snapshot.json").read_text(encoding="utf-8"))
        saved = json.loads((fallback / "result.json").read_text(encoding="utf-8"))
        check(
            "D0 fallback 与课堂使用同一个 baseline 和同一个任务",
            metadata.get("kind") == "SAVED_EVIDENCE"
            and saved.get("baseline_digest") == tree_digest(BASELINE)
            and saved.get("final_test_passed") is True
            and saved.get("tests_modified") is False,
        )
    else:
        check("D0 fallback 已保存", False, "缺少 instructor/d0/fallback（请先完成一次成功预跑）")

    if problems:
        print("\nOVERALL: BLOCKER", problems)
        return 1
    print("\nOVERALL: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
