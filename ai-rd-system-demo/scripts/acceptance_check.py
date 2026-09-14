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
        and 'data-copy="d4-fresh-task"' in html_runbook
        and 'data-copy="d4-inject"' in html_runbook
        and 'data-copy="d4-verify-block"' in html_runbook
        and 'data-copy="d4-restore"' in html_runbook
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
    demo4_pre_baseline = ROOT / "instructor/baselines/demo4-sedimentation"
    demo4_sedimented_baseline = ROOT / "instructor/baselines/demo4-sedimented"

    reset_demo4 = run([str(ROOT / "scripts/reset_demo4.sh")], ROOT)
    check("Demo 4 reset script runs", reset_demo4.returncode == 0, reset_demo4.stderr.strip())
    check(
        "Demo 4 reset state has no sedimented assets yet (D3 fixed, nothing sedimented)",
        not (demo4 / "docs/rules/export_eligibility.md").exists() and not (demo4 / "golden").exists(),
    )
    pre_verify_sh = (demo4 / "verify.sh").read_text(encoding="utf-8")
    check(
        "Demo 4 reset verify.sh is dev-only, no Golden gate yet",
        "pytest" in pre_verify_sh and "golden" not in pre_verify_sh,
    )
    pre_result = run([sys.executable, "-m", "pytest", "-q"], demo4)
    check(
        "Demo 4 reset state: developer tests already green (D3 fix carried over)",
        pre_result.returncode == 0 and "19 passed" in pre_result.stdout,
        pre_result.stdout.strip().splitlines()[-1] if pre_result.stdout else pre_result.stderr.strip(),
    )

    rule_doc = (demo4_sedimented_baseline / "docs/rules/export_eligibility.md").read_text(encoding="utf-8")
    required_rule_tokens = [
        "只有 `APPROVED`、`FUNDED` 允许进入放款处理导出",
        "`SUBMITTED`、`REJECTED` 仍然必须可以在列表查询里正常查到，但不得出现在导出结果里",
        "tenant 数据权限范围",
        "Owner",
        "如何验证",
    ]
    check("Demo 4 sedimented rule doc covers the confirmed rules", all(token in rule_doc for token in required_rule_tokens))

    demo4_report = (demo4_pre_baseline / "reports/demo3-validation.md").read_text(encoding="utf-8")
    check(
        "Demo 4 has a financing-flavored D3 validation report as sedimentation fact input",
        "Overall: PASS" in demo4_report
        and "GC-02" in demo4_report
        and "GC-04" in demo4_report
        and "已经通过独立验收确认的事实" in demo4_report,
    )
    check(
        "Demo 4 validation report is carried forward unchanged into the sedimented baseline",
        (demo4_sedimented_baseline / "reports/demo3-validation.md").read_text(encoding="utf-8") == demo4_report,
    )

    stale_refs = ["export_eligibility_source_of_truth.md", "PROJECT-MEMORY.md"]
    for label, service_path in (
        ("pre-sedimentation", demo4_pre_baseline / "app/financing/service.py"),
        ("sedimented", demo4_sedimented_baseline / "app/financing/service.py"),
    ):
        service_text = service_path.read_text(encoding="utf-8")
        leaks = [token for token in stale_refs if token in service_text]
        check(f"Demo 4 {label} service.py has no dangling source-of-truth/PROJECT-MEMORY references", not leaks, ", ".join(leaks))
    sedimented_service_text = (demo4_sedimented_baseline / "app/financing/service.py").read_text(encoding="utf-8")
    check(
        "Demo 4 sedimented service.py points to the rule doc instead of restating the rule",
        "docs/rules/export_eligibility.md" in sedimented_service_text
        and required_rule_tokens[0] not in sedimented_service_text,
    )

    retro_prompt = (ROOT / "instructor/prompts/demo4/01-retro-sedimentation.md").read_text(encoding="utf-8")
    fresh_prompt = (ROOT / "instructor/prompts/demo4/02-fresh-session-maintenance-task.md").read_text(encoding="utf-8")
    check(
        "Demo 4 retro task tells the agent not to refactor unrelated code (keeps regression injection stable)",
        "不要顺手重构" in retro_prompt and "变量命名" in retro_prompt,
    )
    check(
        "Demo 4 fresh-session task tells the agent not to refactor unrelated code",
        "不要重构你不需要改的代码" in fresh_prompt,
    )
    check(
        "Demo 4 sedimented AGENTS.md carries the same minimal-diff discipline for any future session",
        "不要顺手重构" in (demo4_sedimented_baseline / "AGENTS.md").read_text(encoding="utf-8"),
    )

    golden_cases = json.loads((demo4_sedimented_baseline / "golden/cases.json").read_text(encoding="utf-8"))
    check(
        "Demo 4 Golden Case covers GC-01..GC-04 with independently-derived expected ids",
        {c["id"] for c in golden_cases} >= {"GC-01", "GC-02", "GC-03", "GC-04"}
        and all({"expected_list_ids", "expected_export_ids"} <= set(c) for c in golden_cases),
    )
    golden_script_text = (demo4_sedimented_baseline / "golden/check_export_eligibility.py").read_text(encoding="utf-8")
    check(
        "Demo 4 Golden Case is HTTP black-box, not a copy of developer unit tests",
        "import app.financing" not in golden_script_text
        and "from app.financing" not in golden_script_text
        and "urlopen" in golden_script_text,
    )

    sedimented_verify_sh = (demo4_sedimented_baseline / "verify.sh").read_text(encoding="utf-8")
    check(
        "Demo 4 sedimented verify.sh is the single entry unifying pytest and the Golden gate",
        "pytest" in sedimented_verify_sh
        and "golden" in sedimented_verify_sh
        and "OVERALL" in sedimented_verify_sh,
    )

    sedimented_agents = (demo4_sedimented_baseline / "AGENTS.md").read_text(encoding="utf-8")
    rule_marker = required_rule_tokens[0]
    check(
        "Demo 4 sedimented AGENTS.md points to the rule doc and verify.sh without duplicating rule text",
        "docs/rules/export_eligibility.md" in sedimented_agents
        and "./verify.sh" in sedimented_agents
        and rule_marker not in sedimented_agents,
    )
    rule_marker_locations = {
        str(path.relative_to(demo4_sedimented_baseline))
        for path, text in text_files(demo4_sedimented_baseline)
        if rule_marker in text
    }
    check(
        "Demo 4 confirmed-rule text lives in exactly one discoverable file, not copy-pasted",
        rule_marker_locations == {"docs/rules/export_eligibility.md"},
        ", ".join(sorted(rule_marker_locations)),
    )

    # 端到端资产链路，作用在真实的 workspaces/demo4-sedimentation 上，和课堂用的是同一套脚本：
    # 沉淀态 verify.sh PASS → 注入历史回归确定性 BLOCK → 恢复后再次 PASS。
    sediment_result = run([str(ROOT / "scripts/restore_demo4_sedimented.sh")], ROOT)
    check(
        "Demo 4 restore-sedimented: verify.sh is PASS (rule/golden/verify all wired up)",
        sediment_result.returncode == 0 and "OVERALL: PASS" in sediment_result.stdout,
        sediment_result.stdout.strip().splitlines()[-1] if sediment_result.stdout else sediment_result.stderr.strip(),
    )

    inject_result = run([str(ROOT / "scripts/inject_demo4_regression.sh")], ROOT)
    check("Demo 4 inject-regression script runs deterministically", inject_result.returncode == 0, inject_result.stdout.strip())

    blocked_result = run([str(demo4 / "verify.sh")], demo4)
    check(
        "Demo 4 injected regression: verify.sh deterministically BLOCKED, Golden Case names the 未通过/REJECTED case",
        blocked_result.returncode != 0
        and "Export eligibility Golden Case: FAIL" in blocked_result.stdout
        and "GC-02" in blocked_result.stdout
        and "未通过" in blocked_result.stdout
        and "OVERALL: BLOCKED" in blocked_result.stdout,
        blocked_result.stdout.strip().splitlines()[-1] if blocked_result.stdout else blocked_result.stderr.strip(),
    )

    restore_fixed_result = run([str(ROOT / "scripts/restore_demo4_fixed.sh")], ROOT)
    check(
        "Demo 4 restore-fixed: verify.sh is PASS again without touching sedimented assets",
        restore_fixed_result.returncode == 0 and "OVERALL: PASS" in restore_fixed_result.stdout,
        restore_fixed_result.stdout.strip().splitlines()[-1] if restore_fixed_result.stdout else restore_fixed_result.stderr.strip(),
    )
    check(
        "Demo 4 restore-fixed left the sedimented assets untouched",
        tree_digest(demo4) == tree_digest(demo4_sedimented_baseline),
    )

    # 恢复到 D4-1 的起点（未沉淀），保证本脚本可重复运行、不残留课堂状态。
    run([str(ROOT / "scripts/reset_demo4.sh")], ROOT)

    demo4_leak_text = "\n".join(text for _, text in text_files(demo4_pre_baseline)) + "\n".join(
        text for _, text in text_files(demo4_sedimented_baseline)
    )
    check(
        "Demo 4 has no leftover old settlement/FX_LOSS content",
        "settlement" not in demo4_leak_text and "FX_LOSS" not in demo4_leak_text,
    )
    check(
        "Demo 4 old settlement scripts/assets are gone",
        not (ROOT / "scripts/restore_demo4_before.sh").exists()
        and not (ROOT / "scripts/restore_demo4_learned.sh").exists()
        and not (ROOT / "instructor/golden").exists()
        and not (ROOT / "instructor/baselines/demo4-learned").exists(),
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
