#!/usr/bin/env python3
"""Local-only Test Execution Observer server."""

from __future__ import annotations

import argparse
import json
import re
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from typing import List, Optional

# 支持课堂命令 `python instructor/observer_server.py` 直接运行。
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from instructor.classroom_runbook_server import RUNBOOK_PATH, runtime_payload
from instructor.observer_events import read_current, read_events, reset_observer


OBSERVER_HTML = Path(__file__).resolve().parent / "observer.html"
HOST = "127.0.0.1"
PORT = 8765


def _current_analysis_path(current: dict) -> Optional[Path]:
    run_id = current.get("run_id")
    if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9._-]+", run_id):
        return None
    runs_root = (ROOT / "artifacts" / "runs").resolve()
    analysis_path = (runs_root / run_id / "agent-analysis.md").resolve()
    if analysis_path.parent.parent != runs_root or analysis_path.name != "agent-analysis.md":
        return None
    try:
        return analysis_path if analysis_path.is_file() else None
    except OSError:
        return None


def _analysis_payload(current: dict) -> dict:
    analysis_path = _current_analysis_path(current)
    if analysis_path is None:
        return {}
    try:
        content = analysis_path.read_text(encoding="utf-8")
    except OSError:
        return {}
    labels = {
        "Engineering Execution": "engineering_execution",
        "Test Run Result": "test_run_result",
        "Failure Cause": "failure_cause",
        "Retry Decision": "retry_decision",
        "Recommended Action": "recommended_action",
    }
    fields = {}
    for line in content.splitlines():
        stripped = line.strip()
        for label, key in labels.items():
            prefix = "- " + label + ":"
            if stripped.startswith(prefix):
                fields[key] = stripped[len(prefix):].strip() or "Not available"
    failed_scenarios = []
    in_failed_scenarios = False
    scenario = None
    scenario_labels = {
        "Scenario": "scenario",
        "Failure Cause": "failure_cause",
        "Retry Decision": "retry_decision",
        "Recommended Action": "recommended_action",
        "Evidence": "evidence",
    }
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            in_failed_scenarios = stripped == "## Failed Scenarios"
            if scenario is not None:
                failed_scenarios.append(scenario)
                scenario = None
            continue
        if not in_failed_scenarios or not stripped.startswith("- "):
            continue
        label, separator, value = stripped[2:].partition(":")
        if not separator or label not in scenario_labels:
            continue
        key = scenario_labels[label]
        if key == "scenario":
            if scenario is not None:
                failed_scenarios.append(scenario)
            scenario = {field: "Not available" for field in scenario_labels.values()}
        if scenario is not None:
            scenario[key] = value.strip() or "Not available"
    if scenario is not None:
        failed_scenarios.append(scenario)
    return {
        "status": "READY",
        "url": "/analysis",
        "fields": fields,
        "failed_scenarios": failed_scenarios,
    }


def observer_payload() -> dict:
    current = read_current()
    analysis = _analysis_payload(current)
    return {"current": current, "agent_analysis": analysis or None}


def classroom_runtime_payload() -> dict:
    payload = runtime_payload()
    payload["runbook_url"] = f"http://{HOST}:{PORT}/classroom-runbook.html"
    return payload


class ObserverHandler(BaseHTTPRequestHandler):
    server_version = "TestExecutionObserver/1.0"

    def send_bytes(self, body: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, value: dict, status: int = 200) -> None:
        self.send_bytes(
            json.dumps(value, ensure_ascii=False).encode("utf-8"),
            "application/json; charset=utf-8",
            status,
        )

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        parsed = urlsplit(self.path)
        if parsed.path in ("/", "/observer.html"):
            try:
                body = OBSERVER_HTML.read_bytes()
            except OSError:
                self.send_bytes(b"Observer HTML is unavailable.\n", "text/plain; charset=utf-8", 500)
                return
            self.send_bytes(body, "text/html; charset=utf-8")
            return
        if parsed.path == "/classroom-runbook.html":
            try:
                body = RUNBOOK_PATH.read_bytes()
            except OSError:
                self.send_bytes(b"Runbook HTML is unavailable.\n", "text/plain; charset=utf-8", 500)
                return
            self.send_bytes(body, "text/html; charset=utf-8")
            return
        if parsed.path == "/analysis":
            analysis_path = _current_analysis_path(read_current())
            if analysis_path is None:
                self.send_bytes(b"Analysis is unavailable.\n", "text/plain; charset=utf-8", 404)
                return
            try:
                body = analysis_path.read_bytes()
            except OSError:
                self.send_bytes(b"Analysis is unavailable.\n", "text/plain; charset=utf-8", 404)
                return
            self.send_bytes(body, "text/markdown; charset=utf-8")
            return
        if parsed.path == "/api/current":
            self.send_json(observer_payload())
            return
        if parsed.path == "/api/events":
            query = parse_qs(parsed.query)
            try:
                limit = int(query.get("limit", [30])[0])
            except (TypeError, ValueError):
                limit = 30
            self.send_json({"events": read_events(limit)})
            return
        if parsed.path == "/api/runtime":
            self.send_json(classroom_runtime_payload())
            return
        self.send_bytes(b"Not found\n", "text/plain; charset=utf-8", 404)

    def do_POST(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        if urlsplit(self.path).path != "/api/reset":
            self.send_bytes(b"Not found\n", "text/plain; charset=utf-8", 404)
            return
        try:
            reset_observer()
        except OSError as error:
            self.send_json({"error": str(error)}, status=500)
            return
        self.send_json({"status": "RESET"})

    def log_message(self, format: str, *args: object) -> None:
        print(f"[observer] {self.address_string()} - {format % args}")


class LocalOnlyHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--open", action="store_true", help="启动后打开 Observer 页面")
    parser.add_argument("--reset", action="store_true", help="只清理 artifacts/observer/ 后退出")
    args = parser.parse_args(argv)
    if args.reset:
        reset_observer()
        print("Observer runtime reset: artifacts/observer/")
        return 0

    server = LocalOnlyHTTPServer((HOST, PORT), ObserverHandler)
    url = f"http://{HOST}:{PORT}/"
    print(f"Test Execution Observer: {url}")
    print(f"Classroom Runbook: {url}classroom-runbook.html")
    if args.open:
        threading.Timer(0.2, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nTest Execution Observer stopped.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
