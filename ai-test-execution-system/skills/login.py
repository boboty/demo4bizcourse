"""Skill: login。"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

from skills.contracts import ExecutionContext, require_step, skill_error
from tools import ui


NAME = "login"
PURPOSE = "通过 UI 输入测试账号并完成登录。"


def _find_ready(driver: Any, locator: Dict[str, str], timeout_seconds: int = 25) -> Dict[str, str]:
    deadline = time.monotonic() + timeout_seconds
    last_error: Optional[Exception] = None
    while time.monotonic() < deadline:
        try:
            return ui.find_element(driver, locator)
        except Exception as error:
            last_error = error
            time.sleep(0.5)
    raise RuntimeError("未找到元素 {0}：{1}".format(locator, last_error))


def login(context: ExecutionContext) -> Dict[str, Any]:
    """输入 case；输出 authenticated/user；失败为 LOGIN_FAILED。"""
    try:
        input_step = require_step(context.case, "login")
        submit_step = require_step(context.case, "submit_login")
        if input_step["text"] != context.case["preconditions"]["test_username"]:
            raise AssertionError("登录账号与 preconditions.test_username 不一致。")
        input_element = _find_ready(context.driver, input_step["locator"])
        ui.input_text(context.driver, input_element, input_step["text"])
        submit_element = _find_ready(context.driver, submit_step["locator"])
        ui.click(context.driver, submit_element)
        message = _find_ready(context.driver, {"using": "css selector", "value": "#login-message"})
        deadline = time.monotonic() + 25
        actual = ""
        while time.monotonic() < deadline:
            actual = ui.get_text(context.driver, message)
            if actual == "登录成功":
                context.user = dict(context.user or {})
                context.user["username"] = input_step["text"]
                return {"authenticated": True, "user": context.user}
            time.sleep(0.5)
        raise AssertionError("登录 UI 断言失败：期望 '登录成功'，实际 {0!r}".format(actual))
    except Exception as error:
        raise skill_error(NAME, "LOGIN_FAILED", error, {"username": "redacted"}) from error
