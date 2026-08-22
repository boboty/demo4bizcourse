"""Workflow: prepare → login → open → pay → API facts → reset。"""

from __future__ import annotations

import urllib.parse
from typing import Any, Callable, Dict

from skills.assert_business_state import assert_business_state
from skills.contracts import ExecutionContext, SkillError
from skills.login import login
from skills.open_pending_order import open_pending_order
from skills.pay_order import pay_order
from skills.prepare_pending_order import prepare_pending_order
from skills.reset_test_state import reset_test_state
from tools import device, ui


NAME = "pay_order_and_verify"
PURPOSE = "完成支付业务目标并独立验证业务事实。"


def pay_order_and_verify(
    context: ExecutionContext,
    create_capabilities: Callable[[Dict[str, Any]], Dict[str, Any]],
    device_health_check: Callable[[Dict[str, Any]], None],
    screenshot_name: str,
) -> Dict[str, Any]:
    """执行固定 Workflow；始终尝试 reset_test_state 并返回可审计 record。"""
    record = context.record
    record["workflow"] = NAME
    record["current_step"] = "prepare_pending_order"
    try:
        prepare_pending_order(context)
        record["prepared_order"] = True

        record["current_step"] = "device_health_check"
        device.device_health_check(device_health_check, context.case)
        record["current_step"] = "create_session"
        device.create_session(context.driver, create_capabilities(context.case))
        record["current_step"] = "open_url"
        page_url = urllib.parse.urljoin(
            context.base_url + "/", context.case["ui"]["url"].lstrip("/")
        )
        ui.open_url(context.driver, page_url)

        record["current_step"] = "login"
        login(context)
        record["current_step"] = "open_pending_order"
        open_pending_order(context)
        record["current_step"] = "pay_order"
        pay_order(context)

        record["current_step"] = "screenshot"
        screenshot_path = context.evidence_dir / screenshot_name
        screenshot_path.write_bytes(ui.screenshot(context.driver))
        record["current_step"] = "assert_business_state"
        assert_business_state(context)
        record["result"] = "PASS"
    except SkillError as error:
        record["error"] = str(error)
        record["failure"] = error.to_dict()
        if context.driver.session_id:
            try:
                (context.evidence_dir / "failure-screenshot.png").write_bytes(ui.screenshot(context.driver))
                (context.evidence_dir / "page-source.html").write_text(
                    ui.get_page_source(context.driver), encoding="utf-8"
                )
                record["failure_evidence"] = "saved"
            except Exception as evidence_error:
                record["failure_evidence_error"] = str(evidence_error)
    except Exception as error:
        record["error"] = str(error)
    finally:
        record["current_step"] = "close_session"
        try:
            device.close_session(context.driver)
        except Exception as error:
            record["session_cleanup_error"] = str(error)
            record["result"] = "FAIL"
        record["current_step"] = "reset_test_state"
        try:
            reset_test_state(context)
        except SkillError as error:
            record["cleanup_error"] = str(error)
            record["cleanup_failure"] = error.to_dict()
            record["result"] = "FAIL"
    return record
