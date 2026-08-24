import inspect
import sys
from pathlib import Path

import scripts.run_pay_order_ios as pay_order
import scripts.run_round2_self_heal as self_heal
import tools.runtime as runtime


ROOT = Path(__file__).resolve().parents[1]


def clear_runtime_env(monkeypatch) -> None:
    monkeypatch.delenv("DEMO_BASE_URL", raising=False)
    monkeypatch.delenv("MAC_LAN_IP", raising=False)


def test_cli_base_url_has_highest_priority(monkeypatch) -> None:
    monkeypatch.setenv("DEMO_BASE_URL", "http://env.example:8000/")
    monkeypatch.setenv("MAC_LAN_IP", "10.20.30.40")
    assert runtime.resolve_demo_base_url("http://cli.example:8000/") == "http://cli.example:8000"


def test_demo_base_url_precedes_mac_lan_ip(monkeypatch) -> None:
    monkeypatch.setenv("DEMO_BASE_URL", "http://demo.example:8000/")
    monkeypatch.setenv("MAC_LAN_IP", "10.20.30.40")
    assert runtime.resolve_demo_base_url() == "http://demo.example:8000"


def test_mac_lan_ip_builds_demo_base_url_without_fallback(monkeypatch) -> None:
    clear_runtime_env(monkeypatch)
    monkeypatch.setenv("MAC_LAN_IP", "10.20.30.40")
    monkeypatch.setattr(runtime, "lan_ip", lambda: (_ for _ in ()).throw(AssertionError("lan_ip fallback called")))
    assert runtime.resolve_demo_base_url() == "http://10.20.30.40:8000"


def test_missing_runtime_values_keep_lan_ip_fallback(monkeypatch) -> None:
    clear_runtime_env(monkeypatch)
    monkeypatch.setattr(runtime, "lan_ip", lambda: "10.20.30.40")
    assert runtime.resolve_demo_base_url() == "http://10.20.30.40:8000"


def test_round1_main_passes_cli_base_url_to_resolver(monkeypatch, tmp_path) -> None:
    received = []
    monkeypatch.setattr(pay_order, "resolve_demo_base_url", lambda value: received.append(value) or "http://resolved:8000")
    monkeypatch.setattr(pay_order, "read_case", lambda _: {"case_id": "test-case"})
    monkeypatch.setattr(pay_order, "latest_batch_dir", lambda: tmp_path / "batch")
    monkeypatch.setattr(
        pay_order,
        "run_once",
        lambda case, base_url, evidence_dir: {"result": "PASS", "cleanup": "PASS"},
    )
    monkeypatch.setattr(sys, "argv", ["run_pay_order_ios.py", "--base-url", "http://cli:8000", "--runs", "1"])
    assert pay_order.main() == 0
    assert received == ["http://cli:8000"]


def test_round1_fail_output_points_to_current_step_and_evidence(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(pay_order, "resolve_demo_base_url", lambda _: "http://resolved:8000")
    monkeypatch.setattr(pay_order, "read_case", lambda _: {"case_id": "test-case"})
    monkeypatch.setattr(pay_order, "latest_batch_dir", lambda: tmp_path / "batch")
    monkeypatch.setattr(
        pay_order,
        "run_once",
        lambda case, base_url, evidence_dir: {
            "result": "FAIL",
            "cleanup": "FAIL",
            "current_step": "pay_order",
            "error": "UI failed",
            "cleanup_error": "cleanup failed",
        },
    )
    monkeypatch.setattr(sys, "argv", ["run_pay_order_ios.py", "--runs", "1"])
    assert pay_order.main() == 1
    output = capsys.readouterr().out
    assert "current_step: pay_order" in output
    assert "error: UI failed" in output
    assert "cleanup_error: cleanup failed" in output
    assert "evidence:" in output


def test_round1_and_round2_use_the_same_resolver() -> None:
    assert pay_order.resolve_demo_base_url is runtime.resolve_demo_base_url
    assert self_heal.resolve_demo_base_url is runtime.resolve_demo_base_url
    assert "resolve_demo_base_url(args.base_url)" in inspect.getsource(self_heal.main)


def test_runbook_demo3_commands_carry_runtime_parameters() -> None:
    html = (ROOT / "instructor" / "classroom-runbook.html").read_text(encoding="utf-8")
    demo3 = html[html.index('id="demo3"') : html.index('id="demo4"')]
    for token in ("<MAC-LAN-IP>", "<IPHONE-UDID>", "<APPLE-TEAM-ID>", "<PERSONAL-WDA-BUNDLE-ID>"):
        assert token in demo3
    assert "MAC_LAN_IP='<MAC-LAN-IP>'" in demo3
    assert "python scripts/run_pay_order_ios.py" in demo3
    assert "python scripts/run_round2_self_heal.py" in demo3
