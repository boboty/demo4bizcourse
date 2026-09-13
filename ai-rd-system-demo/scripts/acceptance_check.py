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
    "demo12-financing",
    "demo3-developer",
    "demo3-validator",
    "demo4-sedimentation",
]
problems: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    print(("PASS" if condition else "BLOCKER"), name, detail)
    if not condition:
        problems.append(name)


GENERATED_PARTS = {"results", "preruns", "captures"}


def text_files(root: Path):
    ignored = {".git", ".venv", "__pycache__", ".pytest_cache"} | GENERATED_PARTS
    for path in root.rglob("*"):
        if path.is_file() and not ignored.intersection(path.parts):
            try:
                yield path, path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_digest(root: Path) -> str:
    entries = []
    ignored = {".git", ".venv", "__pycache__", ".pytest_cache"} | GENERATED_PARTS
    for path in sorted(root.rglob("*")):
        if path.is_file() and not ignored.intersection(path.parts):
            entries.append((str(path.relative_to(root)), digest(path)))
    return hashlib.sha256(json.dumps(entries, ensure_ascii=False).encode()).hexdigest()


def run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)


def start_dev_server(root: Path, port: int) -> subprocess.Popen[str]:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(root) + (os.pathsep + existing_pythonpath if existing_pythonpath else "")
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port)],
        cwd=root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        if process.poll() is not None:
            detail = (process.stderr.read() if process.stderr else "").strip()
            raise RuntimeError(f"dev server exited: {detail}")
        try:
            with urlopen(f"http://127.0.0.1:{port}/api/financing-applications", timeout=0.3) as response:
                if response.status == 200:
                    return process
        except OSError:
            time.sleep(0.05)
    process.terminate()
    raise RuntimeError("dev server did not become ready")


def stop_dev_server(process: subprocess.Popen[str]) -> None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def main() -> int:
    expected_python = ROOT / ".venv" / "bin" / "python"
    check(
        "Python 3.12 root venv",
        sys.version_info[:2] == (3, 12) and Path(sys.executable) == expected_python,
        f"{sys.executable} / Python {sys.version_info.major}.{sys.version_info.minor}",
    )
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

    financing = WORKSPACES / "demo12-financing"
    financing_baseline = ROOT / "instructor/baselines/demo12-financing"
    check("old Demo 1 workspace removed", not (WORKSPACES / "demo1-vague").exists())
    check("old Demo 2 workspace removed", not (WORKSPACES / "demo2-five-elements").exists())
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
    same_baseline = all(digest(financing / rel) == digest(financing_baseline / rel) for rel in common_files)
    check("Demo 1 / Demo 2 share demo12 financing baseline", same_baseline)

    financing_text = "\n".join(text for _, text in text_files(financing))
    financing_forbidden = [
        "五要素",
        "five-elements",
        "task-a-five-elements",
        "task_a_acceptance",
        "独立验收",
        "Golden",
        "golden",
        "参考实现",
        "Demo 3",
        "Demo 4",
        "demo3",
        "demo4",
        "task-b",
        "settlement",
        "FX_LOSS",
        "导出字段必须严格",
        "当前用户的数据权限范围",
    ]
    leaks = [token for token in financing_forbidden if token in financing_text]
    check("Demo12 has no Demo1/2 task or future answer material", not leaks, ", ".join(leaks))
    check("Demo12 has no task package or acceptance script", not (financing / "task-a-five-elements.md").exists() and not (financing / "instructor").exists())
    all_repo_text = list(text_files(ROOT))
    spec_marker = "业务方每天手工导出、肉眼" + "筛选"
    spec_locations = {str(path.relative_to(ROOT)) for path, text in all_repo_text if spec_marker in text}
    check(
        "Demo2 complete Spec only lives in Runbook files",
        spec_locations == {"instructor/DEMO-RUNBOOK.md", "instructor/DEMO-RUNBOOK.html"},
        ", ".join(sorted(spec_locations)),
    )
    direct_task_marker = "给融资申请列表增加客户名称和融资状态" + "筛选，并支持导出。"
    direct_task_locations = {str(path.relative_to(ROOT)) for path, text in all_repo_text if direct_task_marker in text}
    direct_task_allowed_exact = {
        "instructor/DEMO-RUNBOOK.md",
        "instructor/DEMO-RUNBOOK.html",
        "instructor/D1-RUNBOOK.md",
        "instructor/D1-HANDOFF-RUNBOOK.html",
        "instructor/d1/task.txt",
    }
    # D1 工程现场接力 demo 把任务文本写进 TASK.md/feature-list.json 作为工程现场资产
    # 本身（不是从 Runbook 临场粘贴），这是与 Level1/2/3 不同的、故意的设计。
    direct_task_allowed_prefixes = (
        "instructor/baselines/d1-handoff/",
        "instructor/reference/d1-handoff-completed/",
        "instructor/d1/handoff/",
        "workspaces/d1-handoff/",
    )
    direct_task_unexpected = {
        location
        for location in direct_task_locations
        if location not in direct_task_allowed_exact and not location.startswith(direct_task_allowed_prefixes)
    }
    check(
        "Direct Task sources are limited to Runbooks, D1 task source and d1-handoff engineering assets",
        not direct_task_unexpected,
        ", ".join(sorted(direct_task_unexpected)),
    )

    d0_workspace = WORKSPACES / "d0-first-loop"
    check("D0 workspace exists: d0-first-loop", d0_workspace.is_dir())
    check("D0 workspace AGENTS: d0-first-loop", (d0_workspace / "AGENTS.md").is_file())
    if (d0_workspace / "AGENTS.md").is_file():
        d0_agents = (d0_workspace / "AGENTS.md").read_text(encoding="utf-8")
        check(
            "D0 workspace isolation rule: d0-first-loop",
            "当前目录就是本次 D0 的完整项目上下文" in d0_agents
            and "不读取父目录或兄弟 workspace" in d0_agents,
        )
    d0_setup = run([sys.executable, str(ROOT / "scripts/d0_verify.py")], ROOT)
    check(
        "D0 reset, 起点红灯, 目标状态与隔离",
        d0_setup.returncode == 0,
        d0_setup.stdout.strip().splitlines()[-1] if d0_setup.stdout else d0_setup.stderr.strip(),
    )

    d1_setup = run([sys.executable, str(ROOT / "scripts/d1_verify_setup.py")], ROOT)
    check(
        "D1 reset, level environment, isolation and retained QA setup",
        d1_setup.returncode == 0,
        d1_setup.stdout.strip().splitlines()[-1] if d1_setup.stdout else d1_setup.stderr.strip(),
    )
    html_runbook = (ROOT / "instructor/DEMO-RUNBOOK.html").read_text(encoding="utf-8")
    check(
        "HTML Runbook has copy buttons",
        'data-copy="demo1-task"' in html_runbook
        and 'data-copy="demo2-spec"' in html_runbook
        and 'data-copy="d3-validator-first"' in html_runbook
        and 'data-copy="d4-retro"' in html_runbook
        and 'data-copy="d4-variant"' in html_runbook
        and 'data-copy="d4-refine"' in html_runbook
        and "navigator.clipboard.writeText" in html_runbook,
    )

    reset_one = run([str(ROOT / "scripts/reset_demo1.sh")], ROOT)
    reset_one_digest = tree_digest(financing)
    check("reset_demo1 restores demo12 baseline", reset_one.returncode == 0 and reset_one_digest == tree_digest(financing_baseline))
    reset_two = run([str(ROOT / "scripts/reset_demo2.sh")], ROOT)
    reset_two_digest = tree_digest(financing)
    check("reset_demo2 restores demo12 baseline", reset_two.returncode == 0 and reset_two_digest == tree_digest(financing_baseline))
    check("reset_demo1 and reset_demo2 produce identical files", reset_one_digest == reset_two_digest)

    developer = WORKSPACES / "demo3-developer"
    result = run([sys.executable, "-m", "pytest", "-q"], developer)
    check("Demo 3 developer tests green", result.returncode == 0, result.stdout.strip().splitlines()[-1] if result.stdout else result.stderr.strip())
    self_check = run([sys.executable, "bin/self-check"], developer)
    check(
        "Demo 3 developer self-check is PASS but blind to the export rule",
        self_check.returncode == 0
        and "SELF-CHECK: PASS" in self_check.stdout
        and "APPROVED" not in self_check.stdout
        and "FUNDED" not in self_check.stdout,
        self_check.stdout.strip().splitlines()[-1] if self_check.stdout else self_check.stderr.strip(),
    )
    developer_text = "\n".join(text for _, text in text_files(developer))
    developer_forbidden = [
        "export_eligibility_source_of_truth",
        "known_applications",
        "validation/cases",
        "golden",
        "EXPORT_ELIGIBLE_STATUSES",
        "放款处理导出规则",
    ]
    leaks = [token for token in developer_forbidden if token in developer_text]
    check("Demo 3 developer has no independent expected-result assets", not leaks, ", ".join(leaks))

    validator = WORKSPACES / "demo3-validator"
    check(
        "Demo 3 validator has no developer source",
        not (validator / "app").exists() and not (validator / "tests/test_export_eligibility.py").exists(),
    )
    # "../demo3-developer" 会出现在 independent-validation.md 的隔离说明里（明确指示不要读它），
    # 这是正常的；真正不该出现的是任何指向开发工程 Python 模块/路径的代码级引用。
    validator_text = "\n".join(text for _, text in text_files(validator))
    actual_output_text = (validator / "bin/actual-output").read_text(encoding="utf-8")
    validator_path_leaks = [token for token in ("app.financing", "app/financing") if token in validator_text]
    actual_output_path_leaks = [token for token in ("demo3-developer", "app.financing", "app/financing") if token in actual_output_text]
    check(
        "Demo 3 validator is HTTP-only and path-isolated",
        not validator_path_leaks and not actual_output_path_leaks,
        ", ".join(validator_path_leaks + actual_output_path_leaks),
    )

    demo3_validator_script = ROOT / "scripts/demo3_validator.py"
    wrong_port = 8039
    wrong_server = start_dev_server(developer, wrong_port)
    try:
        wrong_result = run(
            [sys.executable, str(demo3_validator_script), "--base-url", f"http://127.0.0.1:{wrong_port}", "--validator-dir", str(validator)],
            ROOT,
        )
    finally:
        stop_dev_server(wrong_server)
    check(
        "Demo 3 wrong HTTP: list still shows REJECTED, export still leaks it (BLOCKER)",
        wrong_result.returncode == 1
        and "GC-01" in wrong_result.stdout
        and "PASS" in wrong_result.stdout.splitlines()[1]
        and "GC-02" in wrong_result.stdout
        and "FAIL" in wrong_result.stdout
        and "Overall: BLOCKER" in wrong_result.stdout,
        wrong_result.stdout.strip(),
    )

    with tempfile.TemporaryDirectory(prefix="demo3-fixed-http-") as temp:
        fixed_root = Path(temp) / "fixed"
        shutil.copytree(ROOT / "instructor/baselines/demo3-fixed", fixed_root)
        fixed_port = 8040
        fixed_server = start_dev_server(fixed_root, fixed_port)
        try:
            fixed_result = run(
                [sys.executable, str(demo3_validator_script), "--base-url", f"http://127.0.0.1:{fixed_port}", "--validator-dir", str(validator)],
                ROOT,
            )
        finally:
            stop_dev_server(fixed_server)
        check(
            "Demo 3 fixed HTTP: export eligibility Golden Case is PASS",
            fixed_result.returncode == 0 and "Overall: PASS" in fixed_result.stdout,
            fixed_result.stdout.strip(),
        )

    demo4 = WORKSPACES / "demo4-sedimentation"
    demo4_baseline = ROOT / "instructor/baselines/demo4-sedimentation"
    initial_agents = (demo4 / "AGENTS.md").read_text(encoding="utf-8")
    initial_checklist = (demo4 / "validation/checklist.md").read_text(encoding="utf-8")
    precedence = "先评估“汇损 + 退税”组合候选"
    check("Demo 4 reset state has no precedence rule", precedence not in initial_agents and precedence not in initial_checklist)

    source_report = (demo4_baseline / "reports/demo3-validation.md").read_text(encoding="utf-8")
    check(
        "Demo 4 source report contains final verified rule",
        "Overall: `PASS`" in source_report
        and "FX_LOSS_PLUS_TAX_REFUND" in source_report
        and "组合候选金额 = 汇损金额 + 退税金额" in source_report
        and "TAX_REFUND_ONLY" in source_report,
    )

    learned_agents = (ROOT / "instructor/golden/AGENTS.learned.md").read_text(encoding="utf-8")
    learned_checklist = (ROOT / "instructor/golden/validation_checklist.learned.md").read_text(encoding="utf-8")
    required_semantics = [
        precedence,
        "FX_LOSS_PLUS_TAX_REFUND",
        "汇损金额 + 退税金额",
        "TAX_REFUND_ONLY",
    ]
    check(
        "Demo 4 learned assets contain executable rule",
        all(token in learned_agents for token in required_semantics)
        and "FX_LOSS_PLUS_TAX_REFUND" in learned_checklist
        and "汇损金额 + 退税金额" in learned_checklist
        and "TAX_REFUND_ONLY" in learned_checklist,
    )

    retro_prompt = (ROOT / "instructor/prompts/demo4/04-retro.md").read_text(encoding="utf-8")
    check(
        "Demo 4 retro prompt requires complete semantics",
        "FX_LOSS_PLUS_TAX_REFUND" in retro_prompt
        and "汇损金额 + 退税金额" in retro_prompt
        and "TAX_REFUND_ONLY" in retro_prompt,
    )

    with tempfile.TemporaryDirectory(prefix="demo4-acceptance-") as temp:
        learned = Path(temp)
        shutil.copytree(demo4, learned / "workspace")
        shutil.copy(ROOT / "instructor/golden/AGENTS.learned.md", learned / "workspace/AGENTS.md")
        shutil.copy(ROOT / "instructor/golden/validation_checklist.learned.md", learned / "workspace/validation/checklist.md")
        learned_text = (learned / "workspace/AGENTS.md").read_text(encoding="utf-8")
        variant = json.loads("{\"fx\":2400,\"refund\":8600,\"excluded\":false}")
        rule_complete = all(token in learned_text for token in required_semantics)
        combined = rule_complete and not variant["excluded"]
        mode = "FX_LOSS_PLUS_TAX_REFUND" if combined else "TAX_REFUND_ONLY"
        amount = variant["fx"] + variant["refund"] if combined else variant["refund"]
        check(
            "Demo 4 new-session variant resolves 11000 from complete rule",
            rule_complete and mode == "FX_LOSS_PLUS_TAX_REFUND" and amount == 11000,
        )

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
