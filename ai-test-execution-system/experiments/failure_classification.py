"""真实执行四类 Failure Cause 样本，并保存分类 evidence。

实验只使用本地 FastAPI Mock 和内存中的 task copy，不修改正式 cases/pay_order.yaml，
也不调用 Round 2 Self-Heal。
"""

from __future__ import annotations

import argparse
import copy
import json
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import patch

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.main import create_app  # noqa: E402
from app.runtime import RuntimeStore  # noqa: E402
from runner.failure_classifier import classify_failure  # noqa: E402
from scripts.run_pay_order_ios import read_case  # noqa: E402
from skills.contracts import ExecutionContext, SkillError  # noqa: E402
from skills.login import login  # noqa: E402
from skills.open_pending_order import open_pending_order  # noqa: E402
from skills.pay_order import pay_order  # noqa: E402
from tools.api import HttpToolError, get  # noqa: E402
from tools import device  # noqa: E402


EXPECTED_FACTS = {
    "order_status": "PAID",
    "payment_count": 1,
    "payment_record.status": "SUCCEEDED",
    "inventory.available_quantity": 9,
}
BASELINE_FACTS = {
    "order_status": "PENDING_PAY",
    "payment_count": 0,
    "inventory.available_quantity": 10,
}


class LocalBrowserDriver:
    """对真实 Mock HTML 执行最小 UI Tool 交互，不伪造支付结果。"""

    def __init__(self, client: TestClient) -> None:
        self.client = client
        self.session_id: Optional[str] = None
        self.page_source_text = ""
        self.values: Dict[str, str] = {}
        self.texts: Dict[str, str] = {}
        self.current_order_id: Optional[str] = None
        self.payment_executed = False

    def create_session(self, capabilities: Dict[str, Any]) -> None:
        del capabilities
        self.session_id = "local-experiment-session"

    def open_url(self, url: str) -> None:
        del url
        response = self.client.get("/")
        response.raise_for_status()
        self.page_source_text = response.text

    def _selector_present(self, selector: str) -> bool:
        if selector.startswith("#"):
            token = selector[1:]
            return 'id="{0}"'.format(token) in self.page_source_text or "id='{0}'".format(token) in self.page_source_text
        if "data-testid" in selector:
            token = selector.split("data-testid", 1)[1].split("'", 2)[1]
            return 'data-testid="{0}"'.format(token) in self.page_source_text or "data-testid='{0}'".format(token) in self.page_source_text
        return selector in self.page_source_text

    def find_element(self, locator: Dict[str, str]) -> Dict[str, str]:
        selector = locator["value"]
        if not self._selector_present(selector):
            raise RuntimeError("local DOM 中不存在 locator")
        return {"selector": selector}

    def input_text(self, element: Dict[str, str], text: str) -> None:
        self.values[element["selector"]] = text

    def click(self, element: Dict[str, str]) -> None:
        selector = element["selector"]
        if selector == "[data-testid='login-button']":
            response = self.client.post("/api/login", json={"username": self.values.get("#username", "")})
            if response.status_code == 200:
                self.texts["#login-message"] = "登录成功"
                order_response = self.client.get(
                    "/api/orders", params={"user_id": response.json()["user"]["id"], "status": "PENDING_PAY"}
                )
                orders = order_response.json()["orders"]
                self.page_source_text += '<button data-testid="pending-order">待付款订单</button>'
                self.current_order_id = orders[0]["id"]
            else:
                self.texts["#login-message"] = "登录失败"
        elif selector == "[data-testid='pending-order']":
            self.texts["#order-detail"] = "订单 {0}，状态：PENDING_PAY".format(self.current_order_id)
            self.page_source_text += '<p id="order-detail">{0}</p>'.format(self.texts["#order-detail"])
            self.page_source_text += '<button id="pay-now">立即支付</button>'
        elif selector in {"#pay-now", "[data-testid='confirm-payment']"}:
            response = self.client.post("/api/orders/{0}/pay".format(self.current_order_id))
            if response.status_code == 200:
                self.payment_executed = True
                self.texts["[data-testid='payment-result']"] = "支付成功"
            else:
                self.texts["[data-testid='payment-result']"] = "支付请求失败"
            self.page_source_text += '<p data-testid="payment-result">{0}</p>'.format(
                self.texts["[data-testid='payment-result']"]
            )

    def get_text(self, element: Dict[str, str]) -> str:
        return self.texts.get(element["selector"], "")

    def screenshot(self) -> bytes:
        return b"round5-local-experiment-evidence"

    def page_source(self) -> str:
        return self.page_source_text

    def quit(self) -> None:
        self.session_id = None


def _client(output_dir: Path) -> TestClient:
    state_path = output_dir / "runtime-state.json"
    return TestClient(create_app(RuntimeStore(state_path)))


def _write_json(path: Path, value: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _save_sample(output_root: Path, name: str, original: Dict[str, Any], evidence: Dict[str, Any]) -> Dict[str, Any]:
    result = classify_failure(evidence)
    sample_dir = output_root / name
    _write_json(sample_dir / "original-result.json", original)
    _write_json(sample_dir / "classifier-result.json", result)
    _write_json(sample_dir / "evidence.json", evidence)
    return result


def _prepare(client: TestClient) -> str:
    assert client.post("/api/reset").status_code == 200
    prepared = client.post("/api/test-data/prepare-pending-order")
    assert prepared.status_code == 200
    return prepared.json()["order_id"]


def _run_ui_payment(client: TestClient, case: Dict[str, Any], product_bug: bool = False) -> Dict[str, Any]:
    order_id = _prepare(client)
    if product_bug:
        assert client.put("/api/config", json={"product_bug_mode": "on"}).status_code == 200
    driver = LocalBrowserDriver(client)
    driver.create_session({})
    driver.open_url("/")
    context = ExecutionContext("http://local", case, driver, Path("."), order_id=order_id, user={"id": "user-course-demo"})
    login(context)
    open_pending_order(context)
    pay_order(context)
    facts = client.get("/api/orders/{0}/facts".format(order_id)).json()
    driver.quit()
    return {"context": context, "facts": facts, "driver": driver}


def run_product_sample(output_root: Path) -> Dict[str, Any]:
    case = read_case(ROOT / "cases" / "pay_order.yaml")
    client = _client(output_root / "product")
    run = _run_ui_payment(client, case, product_bug=True)
    context = run["context"]
    evidence = {
        "service_reachable": True,
        "app_reachable": True,
        "device_preflight": True,
        "session_created": True,
        "page_reached": True,
        "workflow_started": True,
        "failure_stage": "assert_business_state",
        "failure_skill": "assert_business_state",
        "ui_assertion": "PASS",
        "payment_executed": True,
        "actual_facts": run["facts"],
        "expected_facts": EXPECTED_FACTS,
    }
    original = {"result": "FAIL", "error_code": "BUSINESS_STATE_ASSERTION_FAILED", "api_facts": run["facts"]}
    return _save_sample(output_root, "product", original, evidence)


def run_automation_sample(output_root: Path) -> Dict[str, Any]:
    case = copy.deepcopy(read_case(ROOT / "cases" / "pay_order.yaml"))
    for step in case["ui"]["steps"]:
        if step["id"] == "pay_order":
            step["locator"] = {"using": "css selector", "value": "#missing-pay-control"}
    client = _client(output_root / "automation")
    order_id = _prepare(client)
    driver = LocalBrowserDriver(client)
    driver.create_session({})
    driver.open_url("/")
    context = ExecutionContext("http://local", case, driver, Path("."), order_id=order_id, user={"id": "user-course-demo"})
    login(context)
    open_pending_order(context)
    with patch("skills.pay_order.time.monotonic", side_effect=[0.0, 26.0]), patch("skills.pay_order.time.sleep", return_value=None):
        try:
            pay_order(context)
        except SkillError as error:
            error_code = error.code
        else:
            error_code = "NONE"
    facts = client.get("/api/orders/{0}/facts".format(order_id)).json()
    driver.quit()
    evidence = {
        "service_reachable": True,
        "app_reachable": True,
        "device_preflight": True,
        "session_created": True,
        "page_reached": True,
        "workflow_started": True,
        "failure_stage": "locator",
        "failure_skill": "pay_order",
        "payment_executed": False,
        "actual_facts": facts,
        "expected_facts": BASELINE_FACTS,
    }
    original = {"result": "FAIL", "error_code": error_code, "payment_executed": False, "facts": facts}
    return _save_sample(output_root, "automation", original, evidence)


def run_environment_sample(output_root: Path) -> Dict[str, Any]:
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    try:
        get("http://127.0.0.1:{0}/health".format(port), timeout=1)
    except HttpToolError:
        pass
    else:
        raise AssertionError("受控不可用端口意外可访问")
    evidence = {
        "service_reachable": False,
        "app_reachable": False,
        "failure_stage": "health",
        "workflow_started": False,
        "business_prepared": False,
    }
    original = {"result": "FAIL", "error_code": "SERVICE_UNAVAILABLE", "workflow_started": False}
    return _save_sample(output_root, "environment", original, evidence)


def run_device_sample(output_root: Path) -> Dict[str, Any]:
    client = _client(output_root / "device")
    assert client.get("/health").status_code == 200
    def missing_device_preflight(_: Dict[str, Any]) -> None:
        try:
            result = subprocess.run(
                ["xcrun", "devicectl", "device", "info", "details", "--device", "round5-nonexistent-device"],
                text=True,
                capture_output=True,
                check=False,
                timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise RuntimeError("device preflight command failed") from error
        if result.returncode == 0:
            raise AssertionError("受控不存在的 device identifier 意外可访问")
        raise RuntimeError("controlled missing device preflight failed")

    try:
        device.device_health_check(missing_device_preflight, {"device_identifier": "controlled-missing-device"})
    except RuntimeError:
        pass
    else:
        raise AssertionError("受控 Device preflight 意外通过")
    evidence = {
        "service_reachable": True,
        "app_reachable": True,
        "failure_stage": "device_preflight",
        "device_preflight": False,
        "device_identifier_source": "controlled-missing-device",
        "session_created": False,
        "workflow_started": False,
    }
    original = {"result": "FAIL", "error_code": "DEVICE_PREFLIGHT_FAILED", "session_created": False}
    return _save_sample(output_root, "device", original, evidence)


def run_experiments(output_root: Path) -> Dict[str, Any]:
    output_root.mkdir(parents=True, exist_ok=True)
    results = {
        "PRODUCT": run_product_sample(output_root),
        "AUTOMATION": run_automation_sample(output_root),
        "ENVIRONMENT": run_environment_sample(output_root),
        "DEVICE": run_device_sample(output_root),
    }
    unclassified_evidence = {"error_message": "timeout"}
    unclassified = _save_sample(
        output_root,
        "unclassified",
        {"result": "FAIL", "error": "timeout"},
        unclassified_evidence,
    )
    results["UNCLASSIFIED"] = unclassified
    summary = {"samples": results, "categories": sorted(results)}
    _write_json(output_root / "summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=ROOT / "artifacts" / "round5" / "failure-classification")
    args = parser.parse_args()
    summary = run_experiments(args.output_root.resolve())
    print(json.dumps({"categories": summary["categories"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
