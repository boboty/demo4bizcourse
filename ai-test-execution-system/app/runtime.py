"""可重建的本地 Mock 业务状态，不依赖数据库或外部服务。"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from threading import RLock
from typing import Any, Dict, Optional


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STATE_PATH = PROJECT_ROOT / "app" / "data" / "runtime_state.json"

UI_VERSIONS = {"v1", "v2"}
PAYMENT_MODES = {"normal", "timeout_before_commit", "timeout_after_commit"}
PRODUCT_BUG_MODES = {"off", "on"}


class RuntimeStore:
    """以单个 JSON 文件保存课堂状态，方便 shell reset 与运行中 API 共用。"""

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = path or Path(os.environ.get("DEMO_STATE_FILE", DEFAULT_STATE_PATH))
        self._lock = RLock()
        if not self.path.exists():
            self.reset(
                ui_version=os.environ.get("UI_VERSION", "v1"),
                payment_mode=os.environ.get("PAYMENT_MODE", "normal"),
                product_bug_mode=os.environ.get("PRODUCT_BUG_MODE", "off"),
            )

    def _validate_settings(self, ui_version: str, payment_mode: str, product_bug_mode: str) -> None:
        if ui_version not in UI_VERSIONS:
            raise ValueError("ui_version 必须为 v1 或 v2")
        if payment_mode not in PAYMENT_MODES:
            raise ValueError("payment_mode 不受支持")
        if product_bug_mode not in PRODUCT_BUG_MODES:
            raise ValueError("product_bug_mode 必须为 off 或 on")

    def _baseline(self, ui_version: str, payment_mode: str, product_bug_mode: str) -> Dict[str, Any]:
        self._validate_settings(ui_version, payment_mode, product_bug_mode)
        return {
            "settings": {
                "ui_version": ui_version,
                "payment_mode": payment_mode,
                "product_bug_mode": product_bug_mode,
            },
            "users": [{"id": "user-course-demo", "username": "course-demo", "name": "课程测试用户"}],
            "products": [{"id": "product-demo", "name": "课程演示商品", "price_cents": 1990}],
            "inventory": {"product-demo": 10},
            "orders": [
                {
                    "id": "order-001",
                    "user_id": "user-course-demo",
                    "product_id": "product-demo",
                    "quantity": 1,
                    "status": "PENDING_PAY",
                }
            ],
            "payments": [],
        }

    def _read(self) -> Dict[str, Any]:
        with self.path.open("r", encoding="utf-8") as state_file:
            return json.load(state_file)

    def _write(self, state: Dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temp_name = tempfile.mkstemp(prefix="runtime_state_", suffix=".json", dir=str(self.path.parent))
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as state_file:
                json.dump(state, state_file, ensure_ascii=False, indent=2, sort_keys=True)
                state_file.write("\n")
            os.replace(temp_name, self.path)
        except Exception:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
            raise

    def reset(
        self,
        ui_version: str = "v1",
        payment_mode: str = "normal",
        product_bug_mode: str = "off",
    ) -> Dict[str, Any]:
        with self._lock:
            state = self._baseline(ui_version, payment_mode, product_bug_mode)
            self._write(state)
            return state

    def get_settings(self) -> Dict[str, str]:
        with self._lock:
            return dict(self._read()["settings"])

    def configure(self, updates: Dict[str, Optional[str]]) -> Dict[str, str]:
        with self._lock:
            state = self._read()
            settings = state["settings"]
            for key, value in updates.items():
                if value is not None:
                    settings[key] = value
            self._validate_settings(
                settings["ui_version"], settings["payment_mode"], settings["product_bug_mode"]
            )
            self._write(state)
            return dict(settings)

    def login(self, username: str) -> Optional[Dict[str, str]]:
        with self._lock:
            for user in self._read()["users"]:
                if user["username"] == username:
                    return dict(user)
            return None

    def prepare_pending_order(self) -> Dict[str, Any]:
        """准备 API/UI 共用的确定性待付款世界，并返回固定 order_id。"""
        return self.reset()

    def list_orders(self, user_id: str, status: Optional[str] = None) -> list[Dict[str, Any]]:
        with self._lock:
            orders = [order for order in self._read()["orders"] if order["user_id"] == user_id]
            if status:
                orders = [order for order in orders if order["status"] == status]
            return [dict(order) for order in orders]

    def order_facts(self, order_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            state = self._read()
            order = next((item for item in state["orders"] if item["id"] == order_id), None)
            if order is None:
                return None
            payments = [payment for payment in state["payments"] if payment["order_id"] == order_id]
            product = next(item for item in state["products"] if item["id"] == order["product_id"])
            return {
                "order_id": order["id"],
                "order_status": order["status"],
                "payment_count": len(payments),
                "payment_record": dict(payments[0]) if payments else None,
                "inventory": {
                    "product_id": product["id"],
                    "available_quantity": state["inventory"][product["id"]],
                },
            }

    def pay(self, order_id: str) -> tuple[str, Optional[Dict[str, Any]]]:
        """返回 outcome：committed、timeout_before_commit、timeout_after_commit。"""
        with self._lock:
            state = self._read()
            order = next((item for item in state["orders"] if item["id"] == order_id), None)
            if order is None:
                return "not_found", None
            if order["status"] == "PAID":
                return "already_paid", None

            mode = state["settings"]["payment_mode"]
            if mode == "timeout_before_commit":
                return mode, None

            payment = {
                "id": "payment-{0:03d}".format(len(state["payments"]) + 1),
                "order_id": order_id,
                "status": "SUCCEEDED",
                "amount_cents": 1990,
            }
            state["payments"].append(payment)
            order["status"] = "PAID"
            if state["settings"]["product_bug_mode"] == "off":
                state["inventory"][order["product_id"]] -= order["quantity"]
            self._write(state)
            if mode == "timeout_after_commit":
                return mode, dict(payment)
            return "committed", dict(payment)
