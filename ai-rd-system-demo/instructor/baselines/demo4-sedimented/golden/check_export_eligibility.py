#!/usr/bin/env python3
"""放款处理导出资格 Golden Case（policy gate）。

独立于开发测试：期望值直接写在 cases.json 里，来自
docs/rules/export_eligibility.md 描述的业务规则和 app/financing/data.json
里的固定演示数据独立算出——不是从被测系统读取，也不是开发单元测试的复制。

验证方式是真实 HTTP 请求（黑盒），不引入开发方实现模块（app 包）。
默认会自己拉起一个临时的开发服务器；也可以传入一个已经在运行的 base_url，
跳过自启动（用于课堂现场对着 demo4_serve.sh 已经开着的服务验证）。
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
CASES_PATH = Path(__file__).resolve().parent / "cases.json"
DEFAULT_PORT = 8999


def _get(base_url: str, path: str, user: str) -> dict:
    request = Request(f"{base_url}{path}", headers={"X-User": user})
    with urlopen(request, timeout=5) as response:
        return json.load(response)


def _post(base_url: str, path: str, user: str) -> dict:
    request = Request(f"{base_url}{path}", data=b"", headers={"X-User": user}, method="POST")
    with urlopen(request, timeout=5) as response:
        return json.load(response)


def _query_string(query: dict) -> str:
    params = {k: v for k, v in query.items() if v}
    return urlencode(params)


def _start_server(port: int) -> subprocess.Popen:
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port)],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    base_url = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        if process.poll() is not None:
            detail = process.stderr.read() if process.stderr else ""
            raise RuntimeError(f"golden case server exited before ready: {detail}")
        try:
            with urlopen(f"{base_url}/api/financing-applications", timeout=0.3):
                return process
        except OSError:
            time.sleep(0.05)
    process.terminate()
    raise RuntimeError("golden case server did not become ready in time")


def main() -> int:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    base_url = sys.argv[1] if len(sys.argv) > 1 else None
    owns_server = base_url is None
    process = None
    if owns_server:
        process = _start_server(DEFAULT_PORT)
        base_url = f"http://127.0.0.1:{DEFAULT_PORT}"

    print("Export eligibility Golden Case")
    ok = True
    try:
        for case in cases:
            qs = _query_string(case["query"])
            list_body = _get(base_url, f"/api/financing-applications?page_size=100&{qs}", case["user"])
            export_body = _post(base_url, f"/api/financing-applications/export?{qs}", case["user"])
            actual_list_ids = sorted(item["id"] for item in list_body["items"])
            actual_export_ids = sorted(row["id"] for row in export_body["payload"]["rows"])
            expected_list_ids = sorted(case["expected_list_ids"])
            expected_export_ids = sorted(case["expected_export_ids"])

            list_pass = actual_list_ids == expected_list_ids
            export_pass = actual_export_ids == expected_export_ids
            case_pass = list_pass and export_pass
            ok = ok and case_pass

            line = f"{case['id']:<6} {case['label']:<14} {'PASS' if case_pass else 'FAIL'}"
            if not export_pass:
                line += (
                    f"  export expected rows: {len(expected_export_ids)} ids={expected_export_ids},"
                    f" actual: {len(actual_export_ids)} ids={actual_export_ids}"
                )
            elif not list_pass:
                line += f"  list expected ids={expected_list_ids}, actual ids={actual_list_ids}"
            print(line)
    except (OSError, URLError, ValueError, KeyError) as exc:
        print(f"golden case request failed: {exc}", file=sys.stderr)
        ok = False
    finally:
        if process is not None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

    print()
    print("Export eligibility Golden Case:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
