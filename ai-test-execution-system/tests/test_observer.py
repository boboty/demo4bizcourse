import json
import threading
from pathlib import Path
from urllib.request import Request, urlopen

from instructor import observer_events, observer_server


def use_runtime(monkeypatch, tmp_path: Path) -> Path:
    root = tmp_path / "observer"
    monkeypatch.setattr(observer_events, "OBSERVER_ROOT", root)
    monkeypatch.setattr(observer_events, "CURRENT_PATH", root / "current.json")
    monkeypatch.setattr(observer_events, "EVENTS_PATH", root / "events.jsonl")
    return root


def test_publish_event_writes_atomic_current_and_appends_history(monkeypatch, tmp_path: Path) -> None:
    root = use_runtime(monkeypatch, tmp_path)
    replaced = []
    real_replace = observer_events.os.replace
    monkeypatch.setattr(observer_events.os, "replace", lambda source, target: (replaced.append((source, target)), real_replace(source, target))[1])

    observer_events.publish_event(
        source="api",
        demo="demo2",
        stage="facts",
        event="business_assertion",
        status="FAIL",
        actual={"inventory": {"available_quantity": 10}},
        expected={"inventory.available_quantity": 9},
        fact_results={"inventory.available_quantity": "FAIL"},
    )

    current = json.loads((root / "current.json").read_text(encoding="utf-8"))
    history = (root / "events.jsonl").read_text(encoding="utf-8").splitlines()
    assert current["event"] == "business_assertion"
    assert json.loads(history[0])["status"] == "FAIL"
    assert len(replaced) == 1
    assert replaced[0][1] == root / "current.json"


def test_publish_failure_is_fail_open(monkeypatch, tmp_path: Path) -> None:
    use_runtime(monkeypatch, tmp_path)
    monkeypatch.setattr(observer_events, "_append_event", lambda *_args: (_ for _ in ()).throw(OSError("disk full")))
    observer_events.publish_event(source="system", stage="run", event="ignored")


def test_reset_only_removes_observer_runtime(monkeypatch, tmp_path: Path) -> None:
    root = use_runtime(monkeypatch, tmp_path)
    root.mkdir(parents=True)
    (root / "current.json").write_text("{}", encoding="utf-8")
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "keep.txt").write_text("keep", encoding="utf-8")

    observer_events.reset_observer()

    assert not root.exists()
    assert (evidence / "keep.txt").is_file()


def test_observer_server_routes_current_and_reset(monkeypatch, tmp_path: Path) -> None:
    root = use_runtime(monkeypatch, tmp_path)
    observer_events.publish_event(source="system", demo="demo1", stage="run", event="ready")
    server = observer_server.LocalOnlyHTTPServer(("127.0.0.1", 0), observer_server.ObserverHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = "http://127.0.0.1:{0}".format(server.server_address[1])
    try:
        current = json.loads(urlopen(url + "/api/current", timeout=2).read())
        assert current["current"]["event"] == "ready"
        reset_request = Request(url + "/api/reset", method="POST")
        assert json.loads(urlopen(reset_request, timeout=2).read())["status"] == "RESET"
        assert not root.exists()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_agent_analysis_is_shown_only_when_real_file_exists(monkeypatch, tmp_path: Path) -> None:
    use_runtime(monkeypatch, tmp_path)
    monkeypatch.setattr(observer_server, "ROOT", tmp_path)
    run_id = "run-001"
    analysis = tmp_path / "artifacts" / "runs" / run_id / "agent-analysis.md"
    analysis.parent.mkdir(parents=True)
    analysis.write_text(
        "# Test Run Analysis\n\n- Engineering Execution: PASS\n- Test Run Result: FAIL\n",
        encoding="utf-8",
    )
    observer_events.publish_event(source="system", demo="demo4", run_id=run_id, stage="run", event="run_completed")

    payload = observer_server.observer_payload()
    assert payload["agent_analysis"]["status"] == "READY"
    assert payload["agent_analysis"]["fields"]["test_run_result"] == "FAIL"

    analysis.unlink()
    assert observer_server.observer_payload()["agent_analysis"] is None


def test_observer_sources_do_not_copy_required_business_facts() -> None:
    root = Path(__file__).resolve().parents[1]
    sources = "\n".join(
        (root / name).read_text(encoding="utf-8")
        for name in ("instructor/observer_events.py", "instructor/observer_server.py", "instructor/observer.html")
    )
    assert "REQUIRED_FACTS" not in sources
