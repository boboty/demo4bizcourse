#!/usr/bin/env python3
"""Demo 2（/demo/codex-loop）浏览器冒烟验收（可选工具，不属于 pytest 基线）。

使用系统 Python 环境中已安装的 Playwright（async API）驱动真实 Chromium，
不进入 requirements.txt，不影响 .venv 与 ./scripts/test.sh。
脚本自行在 8013 端口启动/停止 uvicorn，覆盖：

- 任务包默认展开且在 1366×768 下可读
- 阶段时长配置：每步 10~60 秒，总计约 5 分钟（不使用随机值）
- 开始/暂停/继续/单步/直接结果/重新演示 六个控制均按预期工作（暂停/继续验证使用页内临时缩短的
  延迟覆盖，只为加速冒烟脚本本身，不改变线上文件；生产延迟配置单独用真实值断言）
- 七个阶段按固定顺序执行，内容与任务包给定文案一致
- 测试阶段第一次即显示 18 passed（不制造人为失败）
- 完成报告显示验收标准 10/10 已覆盖
- Demo 1 与 Demo 2 对照区域可见
- 讲师说明默认折叠，显示偏好与其他 Demo 页面共用同一 sessionStorage key
- 刷新页面恢复初始未运行状态
- 不发出任何网络请求（不调用模型接口，不修改项目文件）
- 全流程无 Console error、无 /favicon.ico 请求
- 正式 /api/users/export 与原四个状态页无回归（复用 demo_stage_smoke_check 的判断口径做一次轻量抽查）

用法：

    python3 scripts/demo_codex_loop_smoke_check.py
"""

from __future__ import annotations

import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
PYTHON_BIN = ROOT_DIR / ".venv" / "bin" / "python"
PORT = 8013
BASE = f"http://127.0.0.1:{PORT}"

try:
    from playwright.async_api import async_playwright
except ModuleNotFoundError:
    sys.exit("未找到 Playwright：请使用已安装 Playwright 的系统 Python 运行本脚本。")

import asyncio  # noqa: E402

results: list[tuple[str, bool, str]] = []

STAGE_TITLES = [
    "01 · 读取任务与项目",
    "02 · 制定计划",
    "03 · 实现功能",
    "04 · 建立验证证据",
    "05 · 运行自动化测试",
    "06 · 真实场景验证",
    "07 · 完成与证据映射",
]


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    stamp = time.strftime("%H:%M:%S")
    print(f"{stamp} [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""), flush=True)


def start_server() -> subprocess.Popen:
    proc = subprocess.Popen(
        [str(PYTHON_BIN), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=ROOT_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(50):
        try:
            if urllib.request.urlopen(f"{BASE}/health", timeout=1).status == 200:
                return proc
        except Exception:
            time.sleep(0.2)
    proc.terminate()
    sys.exit("服务启动失败")


async def js_state(page) -> dict:
    return await page.evaluate(
        "() => ({currentStage: window.currentStage, playing: window.playing,"
        " logBlocks: document.querySelectorAll('.log-block').length,"
        " finalHidden: document.getElementById('final-report').hidden})"
    )


async def run() -> int:
    console_errors: list[str] = []
    favicon_requests: list[str] = []
    all_requests: list[str] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(viewport={"width": 1366, "height": 768})
        page = await context.new_page()
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: console_errors.append(str(exc)))
        page.on("request", lambda req: favicon_requests.append(req.url) if "favicon" in req.url else None)
        page.on("request", lambda req: all_requests.append(req.url))

        # ========== A. 初始状态与任务包 ==========
        resp = await page.goto(f"{BASE}/demo/codex-loop")
        check("页面打开成功", resp is not None and resp.status == 200)
        check("页面标题正确", await page.inner_text("h1") == "Demo 2 · 完整任务包驱动研发闭环")

        state0 = await js_state(page)
        check("初始未运行状态：currentStage=0", state0["currentStage"] == 0, str(state0))
        check("初始完成报告隐藏", state0["finalHidden"] is True)

        task_open = await page.get_attribute("#task-package", "open")
        check("任务包默认展开", task_open is not None)
        task_text = await page.inner_text("#task-package")
        check("任务包包含目标/约束/验收/验证四段", all(
            marker in task_text for marker in ["【任务目标】", "【技术约束】", "【验收标准】", "【验证要求】"]))

        box = await page.locator(".task-col").bounding_box()
        scroll_width = await page.evaluate("document.documentElement.scrollWidth")
        check("任务包区域 1366×768 下可读（首屏内、无横向滚动）",
              box["y"] < 768 and scroll_width <= 1366, f"box_y={box['y']}, scrollWidth={scroll_width}")

        check("讲师说明默认折叠", await page.locator("#instructor-guide").is_hidden())

        prod_delays = await page.evaluate("STAGE_DELAYS_MS")
        check("阶段时长配置：每步 10~60 秒", len(prod_delays) == len(STAGE_TITLES)
              and all(10_000 <= d <= 60_000 for d in prod_delays), str(prod_delays))
        check("阶段时长配置：总计约 5 分钟（300000ms）", sum(prod_delays) == 300_000,
              f"sum={sum(prod_delays)}")

        # ========== B. 单步执行 ==========
        await page.click("#btn-step")
        state1 = await js_state(page)
        check("单步执行后仅推进一个阶段", state1["currentStage"] == 1 and state1["logBlocks"] == 1, str(state1))
        log_text = await page.inner_text("#console-log")
        check("阶段一内容与任务包命令一致", "已读取任务目标、功能要求、技术约束与10项验收标准" in log_text)

        # ========== C. 开始 → 暂停：进度停止推进 ==========
        await page.click("#btn-reset")
        state_after_reset = await js_state(page)
        check("重新演示恢复到未运行状态", state_after_reset["currentStage"] == 0
              and state_after_reset["logBlocks"] == 0 and state_after_reset["finalHidden"] is True,
              str(state_after_reset))
        check("重新演示后“提交任务包”重新可用", not await page.is_disabled("#btn-start"))

        # 生产延迟为 10~60 秒/步，冒烟脚本内临时缩短为 1.2 秒/步以加速验证同一套暂停/继续逻辑，
        # 不修改线上文件；真实生产延迟已在上方用真实值单独断言过。
        await page.evaluate("STAGE_DELAYS_MS = [1200, 1200, 1200, 1200, 1200, 1200, 1200]")

        check("开始前“继续”按钮禁用（尚未开始）", await page.is_disabled("#btn-continue"))
        await page.click("#btn-start")
        check("开始执行后“提交任务包”立即禁用（防止重复启动）", await page.is_disabled("#btn-start"))

        await page.wait_for_timeout(600)  # 第一阶段等待中途暂停：此时 currentStage 仍为 0
        check("暂停按钮开始执行后立即可用", not await page.is_disabled("#btn-pause"))
        running_text = await page.inner_text("#log-running")
        check("执行中提示为正向计时“已用时”，不是预知总时长的倒计时",
              "已用时" in running_text and "剩" not in running_text and "共" not in running_text,
              running_text)
        await page.click("#btn-pause")
        paused_state = await js_state(page)
        check("暂停后“继续”按钮可用（即便仍在第一阶段等待中）", not await page.is_disabled("#btn-continue"))
        await page.wait_for_timeout(1500)
        still_state = await js_state(page)
        check("暂停后阶段不再推进", still_state["currentStage"] == paused_state["currentStage"]
              and still_state["playing"] is False,
              f"paused={paused_state['currentStage']}, after_wait={still_state['currentStage']}")

        # ========== D. 继续：从暂停处恢复（应从剩余时间继续，而不是重新等一整段）==========
        await page.click("#btn-continue")
        resumed_playing = await page.evaluate("window.playing")
        check("继续后恢复自动执行", resumed_playing is True)
        await page.wait_for_timeout(2500)
        after_resume_state = await js_state(page)
        check("继续后按固定顺序推进（非人为失败）",
              after_resume_state["currentStage"] > still_state["currentStage"], str(after_resume_state))

        # ========== E. 直接查看最终结果 ==========
        await page.click("#btn-jump-end")
        final_state = await js_state(page)
        check("直接查看最终结果立即完成全部阶段", final_state["currentStage"] == len(STAGE_TITLES)
              and final_state["finalHidden"] is False, str(final_state))

        stage_titles_in_log = await page.locator(".log-block h3").all_inner_texts()
        check("七个阶段按固定顺序全部出现", stage_titles_in_log == STAGE_TITLES, str(stage_titles_in_log))

        terminal_text = await page.inner_text(".log-terminal")
        check("自动化测试第一次即显示 18 passed（不制造人为失败）",
              "18 passed in 1.84s" in terminal_text, terminal_text[:60])

        report_text = await page.inner_text("#final-report")
        check("完成报告显示验收标准 10/10 已覆盖", "验收标准：10/10 已覆盖" in report_text)
        check("完成报告四项证据映射齐全", all(marker in report_text for marker in
              ["目标：导出全部筛选结果", "边界：空姓名与空结果", "质量：真实有效的xlsx", "回归：列表功能不受影响"]))

        for control_id in ("btn-start", "btn-step", "btn-jump-end", "btn-pause", "btn-continue"):
            disabled = await page.is_disabled(f"#{control_id}")
            check(f"完成后控制按钮 #{control_id} 已禁用", disabled, f"disabled={disabled}")

        # ========== F. Demo 1 / Demo 2 对照 ==========
        comparison_text = await page.inner_text("#comparison")
        check("对照区域包含两条演进路径", "模糊需求驱动" in comparison_text and "完整任务包驱动" in comparison_text)
        check("对照区域标注可见", "问题不是AI不会写，而是工作没有被完整定义。" in comparison_text
              and "不是省掉验证，而是避免验证到最后才发现目标定义不完整。" in comparison_text)

        # ========== G. 讲师说明：显示偏好与其他页面共用 ==========
        await page.click("#btn-toggle-guide")
        check("讲师说明可显示", await page.locator("#instructor-guide").is_visible())
        check("讲师说明显示后默认仍折叠一行", await page.locator("#instructor-guide").get_attribute("open") is None)
        await page.click("#instructor-guide summary")
        guide_text = await page.inner_text("#instructor-guide")
        check("讲师说明四部分内容齐全", all(marker in guide_text for marker in
              ["本轮给AI的命令", "当前演示什么", "固定演示步骤", "本轮结论"]))

        await page.goto(f"{BASE}/demo")
        nav_guide_visible = await page.locator("#instructor-guide").is_visible()
        check("讲师说明偏好带入导航页", nav_guide_visible)

        # ========== H. 刷新恢复初始状态 ==========
        await page.goto(f"{BASE}/demo/codex-loop")
        refreshed_state = await js_state(page)
        check("刷新后恢复初始未运行状态", refreshed_state["currentStage"] == 0
              and refreshed_state["logBlocks"] == 0 and refreshed_state["finalHidden"] is True,
              str(refreshed_state))

        # ========== I. 不发出任何网络请求（纯前端模拟） ==========
        all_requests.clear()
        await page.click("#btn-jump-end")
        await page.wait_for_timeout(200)
        non_asset_requests = [u for u in all_requests if u != f"{BASE}/demo/codex-loop"]
        check("执行全流程不发出任何网络请求（不调用模型接口）", not non_asset_requests, str(non_asset_requests[:3]))

        # ========== J. 正式接口与原四个状态页无回归（轻量抽查）==========
        with urllib.request.urlopen(f"{BASE}/api/users/export", timeout=5) as formal:
            check("正式 /api/users/export 无回归", formal.status == 200, f"HTTP {formal.status}")
        base_resp = await page.goto(f"{BASE}/demo/users/base")
        check("原四个状态页无回归（Base 可正常打开）",
              base_resp is not None and base_resp.status == 200
              and await page.inner_text("#stage-badge") == "DEMO 00 · BASELINE")

        # ========== K. Console 与 favicon ==========
        check("全流程无 Console error", not console_errors, "; ".join(console_errors[:3]))
        check("无 /favicon.ico 请求", not favicon_requests, "; ".join(favicon_requests[:3]))

        await browser.close()

    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} 项通过")
    return 1 if failed else 0


def main() -> int:
    server = start_server()
    try:
        return asyncio.run(run())
    finally:
        server.terminate()
        server.wait(timeout=5)


if __name__ == "__main__":
    sys.exit(main())
