#!/usr/bin/env python3
"""不调用模型的 D1 可重复性与隔离预检。"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "instructor" / "baselines" / "demo12-financing"
IGNORED = {".pytest_cache", "__pycache__", ".d1-harness"}
problems: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    print(("PASS" if condition else "BLOCKER"), name, detail)
    if not condition:
        problems.append(name)


def files(root: Path) -> dict[str, bytes]:
    result: dict[str, bytes] = {}
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if path.is_file() and not IGNORED.intersection(path.parts):
            result[str(relative)] = path.read_bytes()
    return result


def digest(root: Path) -> str:
    entries = [(path, hashlib.sha256(data).hexdigest()) for path, data in sorted(files(root).items())]
    return hashlib.sha256(json.dumps(entries, ensure_ascii=False).encode()).hexdigest()


def main() -> int:
    reset = subprocess.run([str(ROOT / "scripts" / "reset_d1.sh"), "both"], cwd=ROOT, text=True, capture_output=True, check=False)
    a = ROOT / "workspaces" / "d1-harness-a"
    b = ROOT / "workspaces" / "d1-harness-b"
    check("D1 reset succeeds", reset.returncode == 0, reset.stderr.strip())
    check("Harness A matches frozen baseline", digest(a) == digest(BASELINE))
    check("Harness B business source matches frozen baseline", digest(b) == digest(BASELINE))
    check("A/B data is identical", (a / "app/financing/data.json").read_bytes() == (b / "app/financing/data.json").read_bytes())
    check("A/B AGENTS is identical", (a / "AGENTS.md").read_bytes() == (b / "AGENTS.md").read_bytes())
    workspace_text = "\n".join(
        path.read_text(encoding="utf-8")
        for workspace in (a, b)
        for path in workspace.rglob("*")
        if path.is_file() and not path.name.endswith(".pyc")
    )
    task = (ROOT / "instructor" / "d1" / "task.txt").read_text(encoding="utf-8").strip()
    task_leaks = [token for token in (task, "independent_acceptance", "task_a_acceptance") if token in workspace_text]
    check("D1 workspaces do not contain task or acceptance implementation", not task_leaks, ", ".join(task_leaks))
    check("Harness B has no extra helper treatment", digest(b) == digest(BASELINE))
    reference = ROOT / "instructor" / "baselines" / "demo12-reference"
    acceptance = subprocess.run(
        [str(ROOT / ".venv/bin/python"), str(ROOT / "instructor/d1/independent_acceptance.py"), "--workspace", str(reference), "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    try:
        result = json.loads(acceptance.stdout)
    except json.JSONDecodeError:
        result = {}
    reference_problems = set(result.get("problems", []))
    check(
        "D1 independent acceptance accepts reference business behavior",
        reference_problems <= {"修改边界受控"} and len(result.get("checks", [])) >= 14,
        acceptance.stderr.strip(),
    )
    print("OVERALL:", "PASS" if not problems else "BLOCKER")
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
