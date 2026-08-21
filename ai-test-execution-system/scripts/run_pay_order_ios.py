#!/usr/bin/env python3
"""Round 1 only: 用 cases/pay_order.yaml 驱动一次真实 iPhone Safari 支付闭环。"""

from __future__ import annotations

import argparse
import base64
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yaml


ROOT = Path(__file__).resolve().parents[1]
ELEMENT_KEY = "element-6066-11e4-a52e-4f735466cecf"
APPIUM_URL = "http://127.0.0.1:4723"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def lan_ip() -> str:
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("8.8.8.8", 80))
        return probe.getsockname()[0]
    finally:
        probe.close()


def request_json(
    url: str, method: str = "GET", payload: Any = None, timeout: int = 90
) -> Tuple[int, Any]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        url, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body) if body else None
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8")
        try:
            parsed = json.loads(body) if body else None
        except json.JSONDecodeError:
            parsed = {"raw_body": body}
        return error.code, parsed
    except urllib.error.URLError as error:
        return 0, {"connection_error": str(error.reason)}


def require_ok(url: str, method: str = "GET", payload: Any = None, timeout: int = 90) -> Any:
    status, body = request_json(url, method, payload, timeout)
    if not 200 <= status < 300:
        raise RuntimeError("{0} {1} 失败（HTTP {2}）：{3}".format(method, url, status, body))
    return body


def read_case(case_path: Path) -> Dict[str, Any]:
    with case_path.open("r", encoding="utf-8") as case_file:
        case = yaml.safe_load(case_file)
    required_paths = (
        "case_id",
        "device.physical",
        "configuration.ui_version",
        "test_data.prepare_pending_order_endpoint",
        "ui.steps",
        "assertions.ui",
        "assertions.api_facts",
        "cleanup.endpoint",
    )
    for path in required_paths:
        value = nested_get(case, path)
        if value in (None, ""):
            raise ValueError("用例缺少必填字段：{0}".format(path))
    if case["device"]["physical"] is not True:
        raise ValueError("Round 1 只能执行 physical: true 的真机用例。")
    if case["configuration"]["ui_version"] != "v1":
        raise ValueError("Round 1 正式执行只能使用 UI V1。")
    return case


def nested_get(value: Any, dotted_path: str) -> Any:
    current = value
    for key in dotted_path.split("."):
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def assert_equals(actual: Dict[str, Any], expected: Dict[str, Any], label: str) -> None:
    mismatches = []
    for dotted_path, wanted in expected.items():
        got = nested_get(actual, dotted_path)
        if got != wanted:
            mismatches.append("{0}: 期望 {1!r}，实际 {2!r}".format(dotted_path, wanted, got))
    if mismatches:
        raise AssertionError("{0}断言失败：{1}".format(label, "; ".join(mismatches)))


class WebDriver:
    def __init__(self) -> None:
        self.session_id: Optional[str] = None

    def command(self, method: str, path: str, payload: Any = None, timeout: int = 90) -> Any:
        body = require_ok(APPIUM_URL + path, method, payload, timeout)
        return body["value"]

    def create_session(self, capabilities: Dict[str, Any]) -> None:
        body = require_ok(APPIUM_URL + "/session", "POST", capabilities, timeout=120)
        session_id = body.get("sessionId")
        if not session_id and isinstance(body.get("value"), dict):
            session_id = body["value"].get("sessionId")
        if not session_id:
            raise RuntimeError("Appium 未返回 sessionId。")
        self.session_id = session_id

    def wait_for_element(self, locator: Dict[str, str], timeout_seconds: int = 25) -> Dict[str, str]:
        last_error: Optional[Exception] = None
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            try:
                element = self.command(
                    "POST", "/session/{0}/element".format(self.session_id), locator, timeout=10
                )
                if element:
                    return element
            except Exception as error:  # Appium 返回 no such element 前继续轮询。
                last_error = error
                time.sleep(0.5)
        raise RuntimeError("未找到元素 {0}：{1}".format(locator, last_error))

    def screenshot(self) -> bytes:
        encoded = self.command("GET", "/session/{0}/screenshot".format(self.session_id))
        return base64.b64decode(encoded)

    def page_source(self) -> str:
        return self.command("GET", "/session/{0}/source".format(self.session_id))

    def wait_for_text(self, locator: Dict[str, str], expected_text: str, timeout_seconds: int = 25) -> str:
        deadline = time.monotonic() + timeout_seconds
        actual_text = ""
        last_error: Optional[Exception] = None
        while time.monotonic() < deadline:
            try:
                element = self.wait_for_element(locator, timeout_seconds=3)
                actual_text = self.command(
                    "GET", "/session/{0}/element/{1}/text".format(self.session_id, element[ELEMENT_KEY])
                )
                if actual_text == expected_text:
                    return actual_text
            except Exception as error:
                last_error = error
            time.sleep(0.5)
        raise AssertionError(
            "UI 断言失败：期望 {0!r}，实际 {1!r}，最后错误：{2}".format(
                expected_text, actual_text, last_error
            )
        )

    def quit(self) -> None:
        if self.session_id:
            try:
                self.command("DELETE", "/session/{0}".format(self.session_id), timeout=30)
            finally:
                self.session_id = None


def appium_capabilities(case: Dict[str, Any]) -> Dict[str, Any]:
    device = case["device"]
    udid = os.environ.get(device["udid_environment"])
    team_id = os.environ.get(device["signing_team_environment"])
    if not udid or not team_id:
        raise RuntimeError(
            "请仅在本机环境中设置 {0} 与 {1}，不要写入 YAML 或 Git。".format(
                device["udid_environment"], device["signing_team_environment"]
            )
        )
    always_match: Dict[str, Any] = {
        "platformName": "iOS",
        "browserName": device["browser"],
        "appium:automationName": "XCUITest",
        "appium:udid": udid,
        "appium:xcodeOrgId": team_id,
        "appium:xcodeSigningId": "Apple Development",
        "appium:newCommandTimeout": 120,
        "appium:webviewConnectTimeout": 30000,
        "appium:showXcodeLog": True,
    }
    wda_bundle = os.environ.get(device["wda_bundle_environment"])
    if wda_bundle:
        always_match["appium:updatedWDABundleId"] = wda_bundle
    return {"capabilities": {"alwaysMatch": always_match, "firstMatch": [{}]}}


def start_appium(log_path: Path) -> subprocess.Popen[str]:
    status, _ = request_json(APPIUM_URL + "/status", timeout=2)
    if status == 200:
        raise RuntimeError("4723 端口已有 Appium 进程；请先停止它再运行本用例。")
    log_file = log_path.open("w", encoding="utf-8")
    process = subprocess.Popen(
        ["appium", "--address", "127.0.0.1", "--port", "4723"],
        stdout=log_file,
        stderr=subprocess.STDOUT,
        text=True,
    )
    # Popen 不会替子进程持有 Python 文件对象；以属性延迟关闭，便于 finally 统一处理。
    process._round1_log_file = log_file  # type: ignore[attr-defined]
    for _ in range(20):
        status, _ = request_json(APPIUM_URL + "/status", timeout=3)
        if status == 200:
            return process
        time.sleep(1)
    process.terminate()
    log_file.close()
    raise RuntimeError("Appium 未能在 4723 端口启动。")


def stop_appium(process: Optional[subprocess.Popen[str]]) -> None:
    if not process:
        return
    process.terminate()
    try:
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        process.kill()
    process._round1_log_file.close()  # type: ignore[attr-defined]


def check_prerequisites(case: Dict[str, Any]) -> None:
    for command in ("appium", "xcrun", "xcodebuild"):
        if not shutil_which(command):
            raise RuntimeError("缺少命令：{0}".format(command))
    installed = subprocess.run(
        ["appium", "driver", "list", "--installed"], text=True, capture_output=True, check=False
    )
    if installed.returncode or "xcuitest" not in (installed.stdout + installed.stderr).lower():
        raise RuntimeError("未安装 Appium XCUITest Driver。")
    udid = os.environ.get(case["device"]["udid_environment"])
    if udid:
        details = subprocess.run(
            ["xcrun", "devicectl", "device", "info", "details", "--device", udid],
            text=True,
            capture_output=True,
            check=False,
        )
        if details.returncode:
            raise RuntimeError("Xcode 无法访问 iPhone；请检查 USB 信任、Developer Mode 与设备解锁。")


def shutil_which(command: str) -> Optional[str]:
    # 避免记录或展示命令搜索路径；真机证据中也不需要本机绝对路径。
    import shutil

    return shutil.which(command)


def execute_ui(driver: WebDriver, case: Dict[str, Any], base_url: str, record: Dict[str, Any]) -> None:
    driver.create_session(appium_capabilities(case))

    page_url = urllib.parse.urljoin(base_url + "/", case["ui"]["url"].lstrip("/"))
    driver.command("POST", "/session/{0}/url".format(driver.session_id), {"url": page_url})
    for step in case["ui"]["steps"]:
        record["current_step"] = step["id"]
        element = driver.wait_for_element(step["locator"])
        element_id = element[ELEMENT_KEY]
        if step["action"] == "input":
            driver.command("POST", "/session/{0}/element/{1}/clear".format(driver.session_id, element_id), {})
            text = step["text"]
            driver.command(
                "POST",
                "/session/{0}/element/{1}/value".format(driver.session_id, element_id),
                {"text": text, "value": list(text)},
            )
        elif step["action"] == "click":
            driver.command("POST", "/session/{0}/element/{1}/click".format(driver.session_id, element_id), {})
        else:
            raise ValueError("不支持的 UI action：{0}".format(step["action"]))

    record["current_step"] = "assert_ui"
    driver.wait_for_text(
        case["assertions"]["ui"]["locator"], case["assertions"]["ui"]["expected_text"]
    )
    record["ui_assertion"] = "PASS"


def run_once(
    case: Dict[str, Any],
    base_url: str,
    evidence_dir: Path,
    configuration_override: Optional[Dict[str, str]] = None,
    round_name: str = "Round 1",
) -> Dict[str, Any]:
    evidence_dir.mkdir(parents=True, exist_ok=False)
    record: Dict[str, Any] = {
        "round": round_name,
        "case_id": case["case_id"],
        "started_at": utc_now(),
        "current_step": "start",
        "result": "FAIL",
    }
    driver = WebDriver()
    appium: Optional[subprocess.Popen[str]] = None
    order_id: Optional[str] = None
    try:
        require_ok(base_url + "/health", timeout=10)
        record["current_step"] = "reset"
        require_ok(base_url + case["test_data"]["reset_endpoint"], "POST")
        expected_configuration = configuration_override or case["configuration"]
        if configuration_override:
            require_ok(base_url + "/api/config", "PUT", configuration_override)
        config = require_ok(base_url + "/api/config")
        assert_equals(config, expected_configuration, "运行配置")

        record["current_step"] = "prepare_pending_order"
        prepared = require_ok(base_url + case["test_data"]["prepare_pending_order_endpoint"], "POST")
        order_id = prepared[case["test_data"]["order_id_response_field"]]
        if not order_id:
            raise AssertionError("prepare API 未返回 order_id。")
        if prepared.get("order_status") != "PENDING_PAY":
            raise AssertionError("prepare API 未准备 PENDING_PAY 订单。")
        record["prepared_order"] = True

        check_prerequisites(case)
        appium = start_appium(evidence_dir / case["evidence"]["appium_log"])
        execute_ui(driver, case, base_url, record)
        (evidence_dir / case["evidence"]["screenshot"]).write_bytes(driver.screenshot())

        record["current_step"] = "assert_api_facts"
        facts_endpoint = case["assertions"]["api_facts"]["endpoint"].format(order_id=order_id)
        facts = require_ok(base_url + facts_endpoint)
        record["api_facts"] = facts
        assert_equals(facts, case["assertions"]["api_facts"]["equals"], "API 业务事实")
        record["api_assertion"] = "PASS"
        record["result"] = "PASS"
    except Exception as error:
        record["error"] = str(error)
        if driver.session_id:
            try:
                (evidence_dir / "failure-screenshot.png").write_bytes(driver.screenshot())
                record["failure_screenshot"] = "saved"
            except Exception as screenshot_error:
                record["failure_screenshot_error"] = str(screenshot_error)
        if order_id:
            try:
                facts_endpoint = case["assertions"]["api_facts"]["endpoint"].format(order_id=order_id)
                record["api_facts"] = require_ok(base_url + facts_endpoint)
            except Exception as facts_error:
                record["api_facts_error"] = str(facts_error)
    finally:
        try:
            driver.quit()
        except Exception as quit_error:
            record["session_cleanup_error"] = str(quit_error)
        stop_appium(appium)
        try:
            record["current_step"] = "cleanup"
            cleaned = require_ok(base_url + case["cleanup"]["endpoint"], "POST")
            cleanup_order_id = cleaned["order_id"]
            cleanup_facts = require_ok(base_url + "/api/orders/{0}/facts".format(cleanup_order_id))
            assert_equals(cleanup_facts, case["cleanup"]["expected_facts"], "cleanup")
            record["cleanup"] = "PASS"
        except Exception as cleanup_error:
            record["cleanup"] = "FAIL"
            record["cleanup_error"] = str(cleanup_error)
            record["result"] = "FAIL"
        record["finished_at"] = utc_now()
        (evidence_dir / case["evidence"]["failure_context"]).write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return record


def latest_batch_dir() -> Path:
    return ROOT / "evidence" / ("round1-" + datetime.now().strftime("%Y%m%d-%H%M%S"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, default=ROOT / "cases" / "pay_order.yaml")
    parser.add_argument("--runs", type=int, default=1, help="连续真实执行次数；稳定性门禁使用 5。")
    parser.add_argument("--base-url", default=os.environ.get("DEMO_BASE_URL"))
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs 必须大于 0")
    case = read_case(args.case)
    base_url = (args.base_url or "http://{0}:8000".format(lan_ip())).rstrip("/")
    batch_dir = latest_batch_dir()
    batch_dir.mkdir(parents=True)
    results = []
    for index in range(1, args.runs + 1):
        record = run_once(case, base_url, batch_dir / "runs" / "run-{0:03d}".format(index))
        results.append({"run": index, "result": record["result"], "cleanup": record.get("cleanup")})
        print("Run {0}/{1}: {2}".format(index, args.runs, record["result"]))
    batch = {"round": "Round 1", "case_id": case["case_id"], "runs": results, "all_pass": all(item["result"] == "PASS" for item in results)}
    (batch_dir / "batch.json").write_text(json.dumps(batch, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(batch, ensure_ascii=False, indent=2))
    return 0 if batch["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
