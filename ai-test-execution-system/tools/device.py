"""Device Tool：只负责设备会话和健康检查。"""

from __future__ import annotations

from typing import Any, Dict


def create_session(driver: Any, capabilities: Dict[str, Any]) -> None:
    driver.create_session(capabilities)


def close_session(driver: Any) -> None:
    driver.quit()


def device_health_check(check: Any, case: Dict[str, Any]) -> None:
    """调用显式提供的环境检查，不改变设备或用例配置。"""
    check(case)
