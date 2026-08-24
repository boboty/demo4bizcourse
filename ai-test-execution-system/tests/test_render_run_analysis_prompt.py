import json
import sys
from pathlib import Path

from scripts import find_latest_complete_run, render_run_analysis_prompt


def write_complete_run(root: Path, run_id: str) -> Path:
    run_dir = root / "artifacts" / "runs" / run_id
    scenario_dir = run_dir / "cases" / "scenario_one"
    scenario_dir.mkdir(parents=True)
    run = {
        "run_id": run_id,
        "suite": "nightly_pay_order",
        "scenarios": [{"scenario_id": "scenario_one", "result": "PASS"}],
    }
    plan = {"plan_id": "nightly_pay_order_plan", "run": run}
    (run_dir / "run.json").write_text(json.dumps(run), encoding="utf-8")
    (run_dir / "run-plan.json").write_text(json.dumps(plan), encoding="utf-8")
    (scenario_dir / "result.json").write_text('{"result":"PASS"}', encoding="utf-8")
    report = root / "reports" / run_id / "report.md"
    report.parent.mkdir(parents=True)
    report.write_text("# Round 4 Run Report\n", encoding="utf-8")
    return run_dir


def test_latest_complete_run_skips_newer_incomplete_directory(tmp_path: Path) -> None:
    expected = write_complete_run(tmp_path, "20260821T153118Z-a0fdb5b3")
    incomplete = tmp_path / "artifacts" / "runs" / "20260821T153119Z-newer"
    incomplete.mkdir(parents=True)
    (incomplete / "run.json").write_text("{}", encoding="utf-8")

    assert find_latest_complete_run.find_latest_complete_run(tmp_path) == expected.resolve()


def test_missing_runs_root_reports_demo4_message(tmp_path: Path) -> None:
    try:
        find_latest_complete_run.find_latest_complete_run(tmp_path)
    except FileNotFoundError as exc:
        assert str(exc) == "No complete Run available for Demo4"
    else:
        raise AssertionError("expected missing Demo4 Run to fail")


def test_analysis_prompt_uses_run_paths_without_leaking_run_answer(tmp_path: Path, monkeypatch, capsys) -> None:
    run_dir = write_complete_run(tmp_path, "20260821T153118Z-a0fdb5b3")
    monkeypatch.setattr(sys, "argv", ["render_run_analysis_prompt.py", str(run_dir)])

    assert render_run_analysis_prompt.main() == 0
    output = capsys.readouterr().out

    assert str((run_dir / "run.json").resolve()) in output
    assert str((run_dir / "run-plan.json").resolve()) in output
    assert str((tmp_path / "reports" / run_dir.name / "report.md").resolve()) in output
    assert str((run_dir / "agent-analysis.md").resolve()) in output
    assert "不重新执行测试" in output
    assert "不修改任何正式测试资产" in output
    assert "不调用 Self-Heal" in output
    assert "product_bug_inventory_not_decremented" not in output
    assert "total=5" not in output


def test_demo4_runbook_has_prompt_to_skill_structure() -> None:
    root = Path(__file__).resolve().parents[1]
    html = (root / "instructor" / "classroom-runbook.html").read_text(encoding="utf-8")
    demo4 = html.split('<section id="demo4"', 1)[1].split('<section id="reset"', 1)[0]
    assert [f'>{title}<' for title in (
        "Existing Automation Foundation",
        "Codex Test Run Analysis",
        "From Prompt to Skill",
    )] == [
        f'>{title}<' for title in (
            "Existing Automation Foundation",
            "Codex Test Run Analysis",
            "From Prompt to Skill",
        ) if f'>{title}<' in demo4
    ]
    assert "Failure Cause / Stability / Test Independence" not in demo4
    assert '<span class="badge fallback">FALLBACK</span>' not in demo4
    assert "Test Run Analysis Skill" in demo4
    assert "高频复用 × 输入输出稳定 × 有明确语义 × 可以独立验收" in demo4

    runbook = (root / "instructor" / "classroom-runbook.md").read_text(encoding="utf-8")
    commands = (root / "instructor" / "commands.md").read_text(encoding="utf-8")
    for content in (runbook, commands):
        assert "find_latest_complete_run.py" in content
        assert "render_run_analysis_prompt.py" in content
        assert "Agent Analysis: READY" in content
        assert "03 From Prompt to Skill" in content or "### 03 From Prompt to Skill" in content
        assert "不得整体删除 `artifacts/runs/`" in content
