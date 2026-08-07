#!/usr/bin/env python3
"""本地浏览器冒烟检查，不访问外部网络，也不写入项目文件。"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
PORT = 8011
BASE = f"http://127.0.0.1:{PORT}"
PYTHON_BIN = Path(os.environ.get("FINANCE_PYTHON", ROOT_DIR / ".venv" / "bin" / "python"))
if not PYTHON_BIN.exists():
    PYTHON_BIN = Path(sys.executable)

try:
    from playwright.async_api import async_playwright
except ModuleNotFoundError:
    sys.exit("未找到 Playwright；请使用已安装 Playwright 的 Python 运行本脚本。")


SCENARIOS = [
    "knowledge-answer",
    "batch-workflow",
    "exception-agent",
    "independent-validation",
    "month-close",
]


def start_server() -> subprocess.Popen[str]:
    process = subprocess.Popen(
        [str(PYTHON_BIN), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=ROOT_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    for _ in range(50):
        try:
            with urllib.request.urlopen(f"{BASE}/health", timeout=1) as response:
                if response.status == 200:
                    return process
        except Exception:
            time.sleep(0.2)
    process.terminate()
    raise RuntimeError("本地服务启动失败")


async def run() -> int:
    checks: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append((name, ok, detail))
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""), flush=True)

    process = start_server()
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            context = await browser.new_context(viewport={"width": 1366, "height": 768})
            page = await context.new_page()
            external_requests: list[str] = []
            console_errors: list[str] = []
            page.on("request", lambda request: external_requests.append(request.url) if not request.url.startswith(BASE) else None)
            page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
            page.on("pageerror", lambda error: console_errors.append(str(error)))

            response = await page.goto(f"{BASE}/demo")
            check("总览页打开", response is not None and response.status == 200)
            check("总览页含五个入口", await page.locator(".overview-card").count() == 5)
            check("总览页无横向滚动", await page.evaluate("document.documentElement.scrollWidth <= 1366"))

            for scenario in SCENARIOS:
                response = await page.goto(f"{BASE}/demo/{scenario}")
                check(f"{scenario} 页面打开", response is not None and response.status == 200)
                check(f"{scenario} 关键控件可见", await page.locator("#btn-next").is_visible() and await page.locator("#btn-reset").is_visible())
                check(f"{scenario} 1366×768 无横向滚动", await page.evaluate("document.documentElement.scrollWidth <= 1366"))
                check(f"{scenario} 讲师说明默认可见", not await page.locator("#instructor-guide").is_hidden())
                judgment_box = await page.locator("#key-judgment").bounding_box()
                check(f"{scenario} 核心判断在首屏", judgment_box is not None and judgment_box["y"] + judgment_box["height"] <= 768)
                await page.click("#btn-guide")
                check(f"{scenario} 可隐藏讲师说明", await page.locator("#instructor-guide").is_hidden())
                await page.click("#btn-guide")
                if scenario == "knowledge-answer":
                    await page.click("[data-fullscreen]")
                    await page.wait_for_timeout(100)
                    check("全屏按钮工作", await page.evaluate("Boolean(document.fullscreenElement)"))
                    await page.click("[data-fullscreen]")
                await page.select_option("#step-select", str(await page.locator("#step-select option").count()))
                check(f"{scenario} 可跳到最终步骤", "第 " in await page.inner_text("#step-count"))
                final_judgment_box = await page.locator("#key-judgment").bounding_box()
                check(f"{scenario} 最终核心判断在首屏", final_judgment_box is not None and final_judgment_box["y"] + final_judgment_box["height"] <= 768)
                await page.click("#btn-reset")
                check(f"{scenario} 重置回到第一步", "第 1 /" in await page.inner_text("#step-count"))

            await page.goto(f"{BASE}/demo/knowledge-answer")
            await page.click("#btn-final")
            check("演示一最终判断", "任务仍待处理" in await page.inner_text("#final-callout"))

            await page.goto(f"{BASE}/demo/batch-workflow")
            await page.click("#btn-final")
            check("演示二批次结果", await page.inner_text("#draft-count") == "37" and await page.inner_text("#investigate-count") == "3")
            await page.click("#btn-exception")
            await page.wait_for_url("**/demo/exception-agent?source=BW-202607-04")
            check("演示二可携带批次跳转演示三", "来自批次 BW-202607-04" in await page.inner_text("#source-badge"))

            await page.select_option("#step-select", "7")
            stop_box = await page.locator(".stop-card").bounding_box()
            check("演示三停止卡片完整显示", await page.locator(".stop-card").is_visible() and "未自动过账" in await page.inner_text(".stop-card") and stop_box is not None and stop_box["y"] + stop_box["height"] <= 768)
            await page.select_option("#step-select", "8")
            check("演示三待确认任务显示", "待人工确认" in await page.inner_text("#evidence-workspace"))

            await page.goto(f"{BASE}/demo/independent-validation")
            await page.click("#btn-final")
            check("演示四独立验收失败", "验收未通过" in await page.inner_text("#validation-workspace"))

            await page.goto(f"{BASE}/demo/month-close")
            await page.select_option("#step-select", "2")
            await page.click("#confirm-close")
            await page.click("#btn-next")
            check("演示五人工确认后生成结转草稿", "已生成草稿" in await page.inner_text("#close-workspace"))

            check("没有外部网络请求", not external_requests, str(external_requests))
            check("没有浏览器错误", not console_errors, str(console_errors))
            await browser.close()
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

    passed = sum(1 for _, ok, _ in checks if ok)
    print(f"\n{passed}/{len(checks)} 项通过")
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
