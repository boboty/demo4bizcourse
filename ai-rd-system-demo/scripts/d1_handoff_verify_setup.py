#!/usr/bin/env python3
"""不调用模型的 D1 工程现场接力 reset / 资产 / 边界预检。"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "workspaces/d1-handoff"
CHECKPOINT = ROOT / "instructor/baselines/d1-handoff/stage-1"
REFERENCE = ROOT / "instructor/reference/d1-handoff-completed"
HANDOFF = ROOT / "instructor/d1/handoff"
problems: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    print(("PASS" if condition else "BLOCKER"), name, detail)
    if not condition:
        problems.append(name)


def run_pytest(workspace: Path) -> subprocess.CompletedProcess[str]:
    python = ROOT / ".venv/bin/python"
    return subprocess.run([str(python), "-m", "pytest", "-q"], cwd=workspace, text=True, capture_output=True, check=False)


def main() -> int:
    reset = subprocess.run([str(ROOT / "scripts/reset_d1_handoff.sh")], cwd=ROOT, text=True, capture_output=True, check=False)
    check("reset_d1_handoff.sh succeeds", reset.returncode == 0, reset.stderr.strip())

    for name in ("TASK.md", "PROGRESS.md", "DECISIONS.md", "feature-list.json", "verify.sh", "AGENTS.md", "PROJECT-MEMORY.md", "CODING-STANDARDS.md"):
        path = WORKSPACE / name
        check(f"workspace has non-empty {name}", path.is_file() and path.stat().st_size > 0)

    check("verify.sh is executable", (WORKSPACE / "verify.sh").stat().st_mode & 0o111 != 0)

    try:
        features = json.loads((WORKSPACE / "feature-list.json").read_text(encoding="utf-8"))
        statuses = {f["id"]: f["status"] for f in features["features"]}
        check(
            "feature-list.json matches handoff checkpoint (customer_name done, others pending)",
            statuses == {"customer_name_filter": "done", "status_filter": "pending", "export_endpoint": "pending"},
            json.dumps(statuses, ensure_ascii=False),
        )
    except Exception as exc:  # noqa: BLE001
        check("feature-list.json is valid and matches handoff checkpoint", False, str(exc))

    log = subprocess.run(["git", "-C", str(WORKSPACE), "log", "--format=%s"], text=True, capture_output=True, check=False)
    commit_messages = log.stdout.strip().splitlines()
    check("workspace has exactly 3 handoff commits", len(commit_messages) == 3, " | ".join(commit_messages))
    check(
        "last commit marks the previous session as ended",
        bool(commit_messages) and "session ended" in commit_messages[0],
        commit_messages[0] if commit_messages else "",
    )
    clean = subprocess.run(["git", "-C", str(WORKSPACE), "status", "--porcelain"], text=True, capture_output=True, check=False)
    check("workspace git state is clean right after reset", clean.stdout.strip() == "")

    verify_result = subprocess.run(["bash", str(WORKSPACE / "verify.sh")], cwd=WORKSPACE, text=True, capture_output=True, check=False)
    check("./verify.sh passes on the frozen handoff checkpoint", verify_result.returncode == 0, verify_result.stdout.strip().splitlines()[-1] if verify_result.stdout else verify_result.stderr.strip())

    check("reference completed implementation exists", REFERENCE.is_dir())
    if REFERENCE.is_dir():
        ref_result = run_pytest(REFERENCE)
        check("reference completed implementation passes its own tests", ref_result.returncode == 0, ref_result.stdout.strip().splitlines()[-1] if ref_result.stdout else ref_result.stderr.strip())
        try:
            ref_features = json.loads((REFERENCE / "feature-list.json").read_text(encoding="utf-8"))
            ref_statuses = {f["id"]: f["status"] for f in ref_features["features"]}
            check("reference feature-list.json marks all three features done", all(v == "done" for v in ref_statuses.values()), json.dumps(ref_statuses, ensure_ascii=False))
        except Exception as exc:  # noqa: BLE001
            check("reference feature-list.json is valid", False, str(exc))

    prompt = HANDOFF / "prompts/handoff.md"
    check("handoff prompt exists and is short (<= 200 chars)", prompt.is_file() and 0 < len(prompt.read_text(encoding="utf-8").strip()) <= 200)

    task_leak_tokens = ["independent_acceptance", "instructor/golden", "settlement_expected.json", "validation/cases.json"]
    workspace_text = "\n".join(
        p.read_text(encoding="utf-8", errors="replace") for p in WORKSPACE.rglob("*") if p.is_file() and ".git" not in p.parts
    )
    leaked = [token for token in task_leak_tokens if token.lower() in workspace_text.lower()]
    check("workspace does not leak lecture-3 assets (Golden Case / independent validator)", not leaked, ", ".join(leaked))

    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for entry in ("workspaces/d1-handoff/", "instructor/d1/handoff/results/", "instructor/d1/handoff/preruns/"):
        check(f".gitignore covers {entry}", entry in gitignore)

    print("OVERALL:", "PASS" if not problems else "BLOCKER")
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
