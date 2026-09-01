#!/usr/bin/env python3
"""不调用模型的三级 reset、环境和 watchdog 预检。"""
from __future__ import annotations
import json, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "instructor/baselines/demo12-financing"
ENVIRONMENT = ROOT / "instructor/d1/environment"
problems: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    print(("PASS" if condition else "BLOCKER"), name, detail)
    if not condition: problems.append(name)


def files(root: Path) -> dict[str, bytes]:
    ignored = {".git", ".pytest_cache", "__pycache__"}
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file() and not ignored.intersection(p.parts)}


def main() -> int:
    reset = subprocess.run([str(ROOT / "scripts/reset_d1.sh"), "all"], cwd=ROOT, text=True, capture_output=True, check=False)
    check("D1 reset succeeds", reset.returncode == 0, reset.stderr.strip())
    levels = {level: ROOT / f"workspaces/d1-{level}" for level in ("level1", "level2", "level3")}
    baseline = files(BASELINE)
    for level, workspace in levels.items():
        current = files(workspace)
        check(f"{level} contains frozen financing baseline", all(current.get(name) == data for name, data in baseline.items()))
        clean = subprocess.run(["git", "-C", str(workspace), "diff", "--exit-code"], capture_output=True, check=False).returncode == 0
        check(f"{level} starts with clean workspace git state", clean)
    check("Level 1 has no project environment", not (levels["level1"] / "PROJECT-MEMORY.md").exists())
    check("Level 2 loads project memory and coding standards", all((levels["level2"] / name).read_bytes() == (ENVIRONMENT / source).read_bytes() for name, source in (("PROJECT-MEMORY.md", "project-memory.md"), ("CODING-STANDARDS.md", "coding-standards.md"))))
    check("Level 3 adds self-check requirements", (levels["level3"] / "SELF-CHECK.md").read_bytes() == (ENVIRONMENT / "self-check.md").read_bytes())
    workspace_text = "\n".join(p.read_text(encoding="utf-8", errors="replace") for w in levels.values() for p in w.rglob("*") if p.is_file() and ".git" not in p.parts)
    task = (ROOT / "instructor/d1/task.txt").read_text(encoding="utf-8").strip()
    leaked = [token for token in (task, "independent_acceptance", "reference") if token.lower() in workspace_text.lower()]
    check("D1 workspaces do not contain task or independent acceptance assets", not leaked, ", ".join(leaked))
    check("All levels share the same baseline data", len({(w / "app/financing/data.json").read_bytes() for w in levels.values()}) == 1)
    check("Watchdog timeout fixture", verify_watchdog())
    reference = ROOT / "instructor/baselines/demo12-reference"
    qa = subprocess.run([str(ROOT / ".venv/bin/python"), str(ROOT / "instructor/d1/independent_acceptance.py"), "--workspace", str(reference), "--json"], cwd=ROOT, text=True, capture_output=True, check=False)
    try: qa_result = json.loads(qa.stdout)
    except json.JSONDecodeError: qa_result = {}
    check(
        "Retained independent acceptance remains available for instructor QA",
        set(qa_result.get("problems", [])) <= {"修改边界受控"} and len(qa_result.get("checks", [])) >= 14,
        qa.stderr.strip(),
    )
    print("OVERALL:", "PASS" if not problems else "BLOCKER")
    return 0 if not problems else 1


def verify_watchdog() -> bool:
    if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
    from instructor.d1 import codex_runner
    class HangingProcess:
        pid = 123456789
        def __init__(self): self.returncode = None; self.calls = 0
        def wait(self, timeout=None):
            self.calls += 1
            if self.calls == 1: raise subprocess.TimeoutExpired("fake-codex", timeout)
            self.returncode = -15; return self.returncode
    with tempfile.TemporaryDirectory(prefix="d1-watchdog-") as temp:
        root = Path(temp); workspace = root / "workspace"; workspace.mkdir(); prompt = root / "prompt.md"; prompt.write_text("Plan", encoding="utf-8")
        trace, last, stderr, status, exit_code = (root / n for n in ("trace", "last", "stderr", "status", "exit"))
        original_popen, original_stop = codex_runner.subprocess.Popen, codex_runner.stop_group; fake = HangingProcess()
        codex_runner.subprocess.Popen = lambda *args, **kwargs: fake; codex_runner.stop_group = lambda *args, **kwargs: None
        original_argv = sys.argv
        sys.argv = ["codex_runner.py", "--workspace", str(workspace), "--prompt", str(prompt), "--trace", str(trace), "--last-message", str(last), "--stderr", str(stderr), "--status", str(status), "--exit-code", str(exit_code), "--sandbox", "read-only", "--timeout-seconds", "1"]
        try: codex_runner.main()
        finally: codex_runner.subprocess.Popen, codex_runner.stop_group, sys.argv = original_popen, original_stop, original_argv
        saved = json.loads(status.read_text(encoding="utf-8")); return saved["status"] == "TIMEOUT" and exit_code.read_text().strip() == "-15"


if __name__ == "__main__": raise SystemExit(main())
