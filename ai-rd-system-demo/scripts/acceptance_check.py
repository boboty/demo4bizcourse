from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACES = ROOT / "workspaces"
NAMES = [
    "demo1-vague",
    "demo2-five-elements",
    "demo3-developer",
    "demo3-validator",
    "demo4-sedimentation",
]
problems: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    print(("PASS" if condition else "BLOCKER"), name, detail)
    if not condition:
        problems.append(name)


def text_files(root: Path):
    ignored = {".git", ".venv", "__pycache__", ".pytest_cache"}
    for path in root.rglob("*"):
        if path.is_file() and not ignored.intersection(path.parts):
            try:
                yield path, path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)


def start_blackbox(root: Path) -> subprocess.Popen[str]:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(root) + (os.pathsep + existing_pythonpath if existing_pythonpath else "")
    process = subprocess.Popen(
        [sys.executable, "-m", "app.settlement.blackbox_server"],
        cwd=root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if process.poll() is not None:
            detail = (process.stderr.read() if process.stderr else "").strip()
            raise RuntimeError(f"blackbox server exited: {detail}")
        try:
            with urlopen("http://127.0.0.1:8765/health", timeout=0.2) as response:
                if response.status == 200:
                    return process
        except OSError:
            time.sleep(0.05)
    process.terminate()
    raise RuntimeError("blackbox server did not become ready")


def stop_blackbox(process: subprocess.Popen[str]) -> None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def main() -> int:
    for name in NAMES:
        workspace = WORKSPACES / name
        check(f"workspace exists: {name}", workspace.is_dir())
        check(f"workspace AGENTS: {name}", (workspace / "AGENTS.md").is_file())
        if (workspace / "AGENTS.md").is_file():
            agents = (workspace / "AGENTS.md").read_text(encoding="utf-8")
            check(
                f"workspace isolation rule: {name}",
                "当前目录就是完整项目上下文" in agents
                and "不读取父目录或兄弟 workspace" in agents,
            )

    common_files = [
        "app/main.py",
        "app/financing/service.py",
        "app/financing/repository.py",
        "static/index.html",
        "tests/test_financing_baseline.py",
        "pyproject.toml",
        "requirements.txt",
        "docs/api.md",
    ]
    same_baseline = all(
        digest(WORKSPACES / "demo1-vague" / rel)
        == digest(WORKSPACES / "demo2-five-elements" / rel)
        for rel in common_files
    )
    check("Demo 1 / Demo 2 identical financing baseline", same_baseline)

    demo1_text = "\n".join(text for _, text in text_files(WORKSPACES / "demo1-vague"))
    demo1_forbidden = [
        "五要素",
        "five-elements",
        "task-a-five-elements",
        "task_a_acceptance",
        "独立验收",
        "Golden",
        "golden",
        "Demo 3",
        "Demo 4",
        "demo3",
        "demo4",
        "task-b",
        "settlement",
        "FX_LOSS",
        "异步导出约束",
    ]
    leaks = [token for token in demo1_forbidden if token in demo1_text]
    check("Demo 1 has no future task or answer material", not leaks, ", ".join(leaks))

    demo2 = WORKSPACES / "demo2-five-elements"
    task_a = (demo2 / "task-a-five-elements.md").read_text(encoding="utf-8")
    required_task_markers = ["背景", "边界", "约束", "交付物", "验收标准"]
    check("Demo 2 contains complete five-elements task", all(marker in task_a for marker in required_task_markers))
    demo2_text = "\n".join(text for _, text in text_files(demo2))
    demo2_forbidden = ["task-b", "Demo 3", "Demo 4", "demo3", "demo4", "settlement", "FX_LOSS", "validation/cases"]
    leaks = [token for token in demo2_forbidden if token in demo2_text]
    check("Demo 2 has no Demo 3 / Demo 4 material", not leaks, ", ".join(leaks))
    check("Demo 2 acceptance script is instructor-only", not (demo2 / "instructor").exists())

    developer = WORKSPACES / "demo3-developer"
    result = run([sys.executable, "-m", "pytest", "-q"], developer)
    check("Demo 3 developer tests green", result.returncode == 0, result.stdout.strip().splitlines()[-1] if result.stdout else result.stderr.strip())
    developer_text = "\n".join(text for _, text in text_files(developer))
    developer_forbidden = ["settlement_expected", "independent_check", "validation/cases", "golden"]
    leaks = [token for token in developer_forbidden if token in developer_text]
    check("Demo 3 developer has no independent expected-result assets", not leaks, ", ".join(leaks))

    validator = WORKSPACES / "demo3-validator"
    check("Demo 3 validator has no developer source", not (validator / "app").exists() and not (validator / "tests/test_settlement_developer.py").exists())
    validator_text = "\n".join(text for _, text in text_files(validator))
    validator_path_leaks = [token for token in ("demo3-developer", "../", "app.settlement", "app/settlement") if token in validator_text]
    check("Demo 3 validator is HTTP-only and path-isolated", not validator_path_leaks, ", ".join(validator_path_leaks))
    expected = {
        "GC-01": {"mode": "FX_LOSS_PLUS_TAX_REFUND", "amount": 6200.0},
        "GC-02": {"mode": "TAX_REFUND_ONLY", "amount": 5000.0},
        "GC-03": {"mode": "TAX_REFUND_ONLY", "amount": 5000.0},
        "GC-04": {"mode": "NO_CANDIDATE", "amount": 0.0},
    }
    wrong_server = start_blackbox(developer)
    try:
        result = run([str(validator / "bin/actual-output"), str(validator / "validation/cases.json")], validator)
    finally:
        stop_blackbox(wrong_server)
    actual = json.loads(result.stdout) if result.returncode == 0 else []
    actual_by_id = {item["id"]: item for item in actual}
    wrong_gc01 = actual_by_id.get("GC-01", {})
    check(
        "Demo 3 wrong HTTP GC-01",
        result.returncode == 0
        and wrong_gc01 == {"id": "GC-01", "mode": "TAX_REFUND_ONLY", "amount": 5000.0},
    )
    validator_lines = ["Independent expectation"]
    for case_id, item in expected.items():
        got = actual_by_id.get(case_id, {})
        actual_amount = got.get("amount", "MISSING")
        if isinstance(actual_amount, (int, float)):
            actual_amount = f"{actual_amount:.0f}"
        validator_lines.append(f"{case_id} expected = {item['amount']:.0f} / {item['mode']}")
        validator_lines.append(f"{case_id} actual = {actual_amount} / {got.get('mode', 'MISSING')}")
    mismatches = [case_id for case_id, item in expected.items() if actual_by_id.get(case_id) != {"id": case_id, **item}]
    validator_lines.append("Overall = BLOCKER" if mismatches else "Overall = PASS")
    validator_output = "\n".join(validator_lines)
    check(
        "Demo 3 validator catches GC-01 blocker",
        result.returncode == 0
        and "GC-01" in mismatches
        and "GC-01 expected = 6200 / FX_LOSS_PLUS_TAX_REFUND" in validator_output
        and "GC-01 actual = 5000 / TAX_REFUND_ONLY" in validator_output
        and "Overall = BLOCKER" in validator_output,
        validator_output.strip(),
    )
    with tempfile.TemporaryDirectory(prefix="demo3-fixed-http-") as temp:
        fixed_root = Path(temp) / "fixed"
        shutil.copytree(ROOT / "instructor/baselines/demo3-fixed", fixed_root)
        fixed_server = start_blackbox(fixed_root)
        try:
            fixed_result = run([str(validator / "bin/actual-output"), str(validator / "validation/cases.json")], validator)
        finally:
            stop_blackbox(fixed_server)
        fixed_actual = json.loads(fixed_result.stdout) if fixed_result.returncode == 0 else []
        fixed_by_id = {item["id"]: item for item in fixed_actual}
        check(
            "Demo 3 fixed HTTP GC-01",
            fixed_result.returncode == 0
            and fixed_by_id.get("GC-01") == {"id": "GC-01", "mode": "FX_LOSS_PLUS_TAX_REFUND", "amount": 6200.0},
        )

    demo4 = WORKSPACES / "demo4-sedimentation"
    initial_agents = (demo4 / "AGENTS.md").read_text(encoding="utf-8")
    initial_checklist = (demo4 / "validation/checklist.md").read_text(encoding="utf-8")
    precedence = "先评估“汇损 + 退税”组合候选"
    check("Demo 4 reset state has no precedence rule", precedence not in initial_agents and precedence not in initial_checklist)
    learned_agents = (ROOT / "instructor/golden/AGENTS.learned.md").read_text(encoding="utf-8")
    learned_checklist = (ROOT / "instructor/golden/validation_checklist.learned.md").read_text(encoding="utf-8")
    check("Demo 4 learned assets contain precedence rule", precedence in learned_agents and "组合候选" in learned_checklist)
    with tempfile.TemporaryDirectory(prefix="demo4-acceptance-") as temp:
        learned = Path(temp)
        shutil.copytree(demo4, learned / "workspace")
        shutil.copy(ROOT / "instructor/golden/AGENTS.learned.md", learned / "workspace/AGENTS.md")
        shutil.copy(ROOT / "instructor/golden/validation_checklist.learned.md", learned / "workspace/validation/checklist.md")
        learned_text = (learned / "workspace/AGENTS.md").read_text(encoding="utf-8")
        variant = json.loads("{\"fx\":2400,\"refund\":8600,\"excluded\":false}")
        combined = precedence in learned_text and not variant["excluded"]
        mode = "FX_LOSS_PLUS_TAX_REFUND" if combined else "TAX_REFUND_ONLY"
        amount = variant["fx"] + variant["refund"] if combined else variant["refund"]
        check("Demo 4 new-session variant resolves 11000", mode == "FX_LOSS_PLUS_TAX_REFUND" and amount == 11000)

    for name in NAMES:
        workspace = WORKSPACES / name
        result = run([sys.executable, "-m", "pytest", "-q"], workspace)
        check(f"standalone pytest: {name}", result.returncode == 0, result.stdout.strip().splitlines()[-1] if result.stdout else result.stderr.strip())

    if problems:
        print("\nOVERALL: BLOCKER", problems)
        return 1
    print("\nOVERALL: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
