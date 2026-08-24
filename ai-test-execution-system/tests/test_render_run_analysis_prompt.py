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
