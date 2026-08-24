import json
from pathlib import Path

from instructor import run_round4_demo


ROOT = Path(__file__).resolve().parents[1]


def write_run(root: Path, run_id: str, complete: bool = True) -> dict:
    run_dir = root / "artifacts" / "runs" / run_id
    scenarios = [
        {"scenario_id": "normal_payment", "result": "PASS"},
        {"scenario_id": "normal_payment_repeat", "result": "PASS"},
        {"scenario_id": "product_bug_inventory_not_decremented", "result": "FAIL"},
        {"scenario_id": "timeout_before_commit_business_retry", "result": "PASS"},
        {"scenario_id": "timeout_after_commit_no_retry", "result": "PASS"},
    ]
    run = {
        "run_id": run_id,
        "suite": "nightly_pay_order",
        "execution_mode": "serial",
        "result": "FAIL",
        "scenarios": scenarios,
    }
    run_dir.mkdir(parents=True)
    (run_dir / "run.json").write_text(json.dumps(run), encoding="utf-8")
    for scenario in scenarios if complete else scenarios[:1]:
        scenario_dir = run_dir / "cases" / scenario["scenario_id"]
        scenario_dir.mkdir(parents=True)
        (scenario_dir / "result.json").write_text(json.dumps(scenario), encoding="utf-8")
    if complete:
        (run_dir / "run-plan.json").write_text(json.dumps({"run": run}), encoding="utf-8")
        report = root / "reports" / run_id / "report.md"
        report.parent.mkdir(parents=True)
        report.write_text("# Round 4 Run Report\n", encoding="utf-8")
    return run


def test_wrapper_hides_raw_run_json_and_returns_zero_for_complete_fail(tmp_path: Path, monkeypatch, capsys) -> None:
    run_id = "20260824T101832Z-00231ba9"
    monkeypatch.setattr(run_round4_demo, "ROOT", tmp_path)
    run = write_run(tmp_path, run_id)

    def fake_run_now(plan_path: Path, base_url=None):
        assert plan_path == tmp_path / "schedules" / "nightly.yaml"
        print(json.dumps({"product_bug_inventory_not_decremented": True, "inventory.available_quantity": 10}))
        return {"run": run}

    monkeypatch.setattr(run_round4_demo, "run_now", fake_run_now)

    assert run_round4_demo.main([]) == 0
    output = capsys.readouterr().out
    assert "Run Plan: COMPLETED" in output
    assert "Run ID: {0}".format(run_id) in output
    assert "Execution Mode: serial" in output
    assert "Scenarios: 5" in output
    assert "Artifacts: READY" in output
    assert "Report: READY" in output
    assert "Ready for Agent Analysis" in output
    assert "product_bug_inventory_not_decremented" not in output
    assert "inventory.available_quantity" not in output
    assert "Test Run Result: FAIL" not in output


def test_wrapper_returns_nonzero_for_exception_or_incomplete_run(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(run_round4_demo, "ROOT", tmp_path)

    def raise_error(plan_path: Path, base_url=None):
        raise RuntimeError("preflight failed")

    monkeypatch.setattr(run_round4_demo, "run_now", raise_error)
    assert run_round4_demo.main([]) == 1
    error_output = capsys.readouterr()
    assert "Run Plan: FAILED" in error_output.err
    assert "Run: READY" not in error_output.out

    run_id = "20260824T101833Z-incomplete"
    run = write_run(tmp_path, run_id, complete=False)
    monkeypatch.setattr(run_round4_demo, "run_now", lambda plan_path, base_url=None: {"run": run})
    assert run_round4_demo.main([]) == 1
    incomplete_output = capsys.readouterr()
    assert "Run Plan: FAILED" in incomplete_output.err
    assert "Artifacts: READY" not in incomplete_output.out


def test_demo4_html_has_four_steps_and_safe_locate_gate() -> None:
    html = (ROOT / "instructor" / "classroom-runbook.html").read_text(encoding="utf-8")
    demo4 = html.split('<section id="demo4"', 1)[1].split('<section id="reset"', 1)[0]
    expected_titles = (
        "Existing Automation Foundation",
        "Execute Test Run",
        "Codex Test Run Analysis",
        "From Prompt to Skill",
    )
    assert demo4.count('class="step"') == 4
    assert all(f">{title}<" in demo4 for title in expected_titles)
    flow = "Existing Automation</div><span class=\"flow-arrow\">→</span><div class=\"flow-node live\">Execute Test Run</div>"
    assert flow in html
    assert "Completed Run</div>" in demo4
    assert "Agent Analysis</div>" in demo4
    assert "Deterministic Rules</div>" in demo4
    assert "Decision</div>" in demo4
    assert "Skill</div>" in demo4
    assert 'if ! RUN_DIR=$(python scripts/find_latest_complete_run.py); then' in demo4
    assert 'echo "Run: MISSING"' in demo4
    assert 'echo "Run: READY"' in demo4
