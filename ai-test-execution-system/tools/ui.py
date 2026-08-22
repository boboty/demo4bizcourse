"""UI Tool：把 WebDriver 的一次动作暴露为可复用原子能力。"""

from __future__ import annotations

from typing import Any, Dict


def find_element(driver: Any, locator: Dict[str, str]) -> Dict[str, str]:
    """查找一次元素；等待/轮询由上层 Skill 明确控制。"""
    return driver.find_element(locator)


def open_url(driver: Any, url: str) -> None:
    """打开一次页面 URL；不包含业务导航或 fallback。"""
    driver.open_url(url)


def input_text(driver: Any, element: Dict[str, str], text: str) -> None:
    driver.input_text(element, text)


def click(driver: Any, element: Dict[str, str]) -> None:
    driver.click(element)


def get_text(driver: Any, element: Dict[str, str]) -> str:
    return driver.get_text(element)


def screenshot(driver: Any) -> bytes:
    return driver.screenshot()


def get_page_source(driver: Any) -> str:
    return driver.page_source()
