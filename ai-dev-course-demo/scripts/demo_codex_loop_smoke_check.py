#!/usr/bin/env python3
"""Demo 2（/demo/codex-loop）浏览器冒烟验收（可选工具，不属于 pytest 基线）。

使用系统 Python 环境中已安装的 Playwright（async API）驱动真实 Chromium，
不进入 requirements.txt，不影响 .venv 与 ./scripts/test.sh。
脚本自行在 8013 端口启动/停止 uvicorn，覆盖新版“主代理调度 + 子代理执行 +
轻量驳回 + 门禁放行”流程：

- 任务包默认展开且在 1366×768 下可读；角色协作流程图与角色图例可见
- 阶段时长配置：每步 10~60 秒（不使用随机值）
- 开始/暂停/继续/单步/直接结果/重新演示 六个控制均按预期工作（暂停/继续验证使用页内临时缩短的
  延迟覆盖，只为加速冒烟脚本本身，不改变线上文件；生产延迟配置单独用真实值断言）
- 八个节点按固定顺序执行，且角色标签（主代理/代码子代理/独立验收代理）与内容一致
- 节点04 只提交新增测试（5 passed），刻意保留“未运行全量回归测试”的轻量缺口
- 节点05 主代理门禁驳回：REJECTED、原因为“验证证据不足”，不是代码错误
- 节点06 补充验证第一次即显示 25 passed（不制造人为失败/多轮驳回）
- 节点07 主代理门禁放行：PASSED
- “当前状态”徽标随节点推进更新（含 GATE REJECTED / GATE PASSED / FINAL PASS）
- 完成报告显示验收项 9/9 已覆盖，并保留四条观点钉子与主结论
- Demo 1 与 Demo 2 对照区域体现新的多智能体流程
- 讲师说明默认折叠，显示偏好与其他 Demo 页面共用同一 sessionStorage key
- 刷新页面恢复初始未运行状态
- 不发出任何网络请求（不调用模型接口，不修改项目文件）
- 全流程无 Console error、无 /favicon.ico 请求
- 正式 /api/users/export 与原四个状态页无回归（轻量抽查）

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
    "01 · 主代理读取任务包",
    "02 · 主代理制定执行计划",
    "03 · 主代理拉起代码子代理",
    "04 · 代码子代理完成实现",
    "05 · 主代理执行阶段门禁并驳回",
    "06 · 代码子代理补充验证",
    "07 · 主代理门禁放行",
    "08 · 独立验收代理最终验收",
]
STAGE_ROLE_ICONS = ["🧭", "🧭", "🧭", "🛠", "🧭", "🛠", "🧭", "✅"]
STAGE_STATUS = [
    "READING", "PLANNING", "DELEGATED", "SUBMITTED",
    "GATE REJECTED", "FIXING / VERIFYING", "GATE PASSED", "FINAL PASS",
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
        " finalHidden: document.getElementById('final-report').hidden,"
        " flowStatus: document.getElementById('flow-status').textContent})"
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

        # ========== A. 初始状态、任务包与角色协作流程图 ==========
        resp = await page.goto(f"{BASE}/demo/codex-loop")
        check("页面打开成功", resp is not None and resp.status == 200)
        check("页面标题正确", await page.inner_text("h1") == "Demo 2 · 完整任务包驱动研发闭环")

        state0 = await js_state(page)
        check("初始未运行状态：currentStage=0", state0["currentStage"] == 0, str(state0))
        check("初始完成报告隐藏", state0["finalHidden"] is True)
        check("初始“当前状态”徽标为占位符", state0["flowStatus"] == "—", state0["flowStatus"])

        task_open = await page.get_attribute("#task-package", "open")
        check("任务包默认展开", task_open is not None)
        task_text = await page.inner_text("#task-package")
        check("任务包包含目标/约束/验收/验证四段", all(
            marker in task_text for marker in ["【任务目标】", "【技术约束】", "【验收标准】", "【验证要求】"]))

        box = await page.locator(".task-col").bounding_box()
        scroll_width = await page.evaluate("document.documentElement.scrollWidth")
        check("任务包区域 1366×768 下可读（首屏内、无横向滚动）",
              box["y"] < 768 and scroll_width <= 1366, f"box_y={box['y']}, scrollWidth={scroll_width}")

        role_legend_text = await page.inner_text(".role-legend")
        check("角色图例区分三个角色", all(
            marker in role_legend_text for marker in ["主代理", "代码子代理", "独立验收代理"]))
        role_flow_text = await page.inner_text(".role-flow")
        check("角色协作流程图包含派发/驳回放行链路", all(
            marker in role_flow_text for marker in ["主代理", "代码子代理", "派发任务", "驳回 / 放行", "独立验收代理"]))

        check("讲师说明默认折叠", await page.locator("#instructor-guide").is_hidden())

        prod_delays = await page.evaluate("STAGE_DELAYS_MS")
        check("阶段时长配置：每步 10~60 秒、共 8 步", len(prod_delays) == len(STAGE_TITLES)
              and all(10_000 <= d <= 60_000 for d in prod_delays), str(prod_delays))

        # ========== B. 单步执行（节点01：主代理读取任务包）==========
        await page.click("#btn-step")
        state1 = await js_state(page)
        check("单步执行后仅推进一个节点", state1["currentStage"] == 1 and state1["logBlocks"] == 1, str(state1))
        check("单步执行后“当前状态”徽标更新为 READING", state1["flowStatus"] == "READING", state1["flowStatus"])
        log_text = await page.inner_text("#console-log")
        check("节点一内容为主代理读取任务包（非旧版单体流程文案）",
              "已读取完整任务包" in log_text and "主代理" in log_text)

        # ========== C. 开始 → 暂停：进度停止推进 ==========
        await page.click("#btn-reset")
        state_after_reset = await js_state(page)
        check("重新演示恢复到未运行状态", state_after_reset["currentStage"] == 0
              and state_after_reset["logBlocks"] == 0 and state_after_reset["finalHidden"] is True,
              str(state_after_reset))
        check("重新演示后“提交任务包”重新可用", not await page.is_disabled("#btn-start"))

        # 生产延迟为 10~60 秒/步，冒烟脚本内临时缩短为 1.2 秒/步以加速验证同一套暂停/继续逻辑，
        # 不修改线上文件；真实生产延迟已在上方用真实值单独断言过。
        await page.evaluate(
            "STAGE_DELAYS_MS = [1200, 1200, 1200, 1200, 1200, 1200, 1200, 1200]"
        )

        check("开始前“继续”按钮禁用（尚未开始）", await page.is_disabled("#btn-continue"))
        await page.click("#btn-start")
        check("开始执行后“提交任务包”立即禁用（防止重复启动）", await page.is_disabled("#btn-start"))

        await page.wait_for_timeout(600)  # 第一节点等待中途暂停：此时 currentStage 仍为 0
        check("暂停按钮开始执行后立即可用", not await page.is_disabled("#btn-pause"))
        running_text = await page.inner_text("#log-running")
        check("执行中提示为正向计时“已用时”，不是预知总时长的倒计时",
              "已用时" in running_text and "剩" not in running_text and "共" not in running_text,
              running_text)
        await page.click("#btn-pause")
        paused_state = await js_state(page)
        check("暂停后“继续”按钮可用（即便仍在第一节点等待中）", not await page.is_disabled("#btn-continue"))
        await page.wait_for_timeout(1500)
        still_state = await js_state(page)
        check("暂停后节点不再推进", still_state["currentStage"] == paused_state["currentStage"]
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

        # ========== E. 直接查看最终结果：校验全部 8 个节点与角色标注 ==========
        await page.click("#btn-jump-end")
        final_state = await js_state(page)
        check("直接查看最终结果立即完成全部节点", final_state["currentStage"] == len(STAGE_TITLES)
              and final_state["finalHidden"] is False, str(final_state))
        check("完成后“当前状态”徽标为 FINAL PASS", final_state["flowStatus"] == "FINAL PASS",
              final_state["flowStatus"])

        stage_titles_in_log = await page.locator(".log-block h3").all_inner_texts()
        check("八个节点按固定顺序全部出现（含角色图标）", stage_titles_in_log == [
            f"{icon} {title}" for icon, title in zip(STAGE_ROLE_ICONS, STAGE_TITLES)
        ], str(stage_titles_in_log))

        role_tags_in_log = await page.locator(".log-role-tag").all_inner_texts()
        check("每个节点标注了角色（主代理/代码子代理/独立验收代理）", role_tags_in_log == [
            "主代理", "主代理", "主代理", "代码子代理", "主代理", "代码子代理", "主代理", "独立验收代理"
        ], str(role_tags_in_log))

        terminal_texts = await page.locator(".log-terminal").all_inner_texts()
        check("节点04（首次提交）只有新增测试 5 passed（刻意的轻量缺口）",
              any("5 passed in 0.31s" in t for t in terminal_texts), str(terminal_texts))
        check("节点06（补充验证）第一次即显示全量 25 passed（不制造人为失败）",
              any("25 passed in 0.42s" in t for t in terminal_texts), str(terminal_texts))

        gap_note_text = await page.inner_text(".log-gap-note")
        check("节点04 明确标注轻量缺口而非代码 Bug", "尚未运行全量回归测试" in gap_note_text)

        # ========== F. 门禁驳回与放行：REJECTED → PASSED ==========
        rejected_box = page.locator(".log-gate-rejected")
        passed_box = page.locator(".log-gate-passed")
        check("门禁驳回面板存在且状态为 REJECTED", await rejected_box.count() == 1
              and "REJECTED" in await rejected_box.inner_text())
        rejected_text = await rejected_box.inner_text()
        check("驳回原因是验证证据不足，不是代码错误",
              "验证证据不足" in rejected_text and "未运行全量测试" in rejected_text
              and "AttributeError" not in rejected_text and "IndexError" not in rejected_text)
        check("门禁放行面板存在且状态为 PASSED", await passed_box.count() == 1
              and "PASSED" in await passed_box.inner_text())

        report_text = await page.inner_text("#final-report")
        check("完成报告显示验收项 9/9 已覆盖", "验收项：9/9 已覆盖" in report_text)
        check("完成报告门禁历史体现一次驳回、一次放行",
              "GATE REJECTED" in report_text and "GATE PASSED" in report_text)
        check("完成报告保留四条观点钉子", all(marker in report_text for marker in [
            "主代理不必亲自执行每一步，但必须掌握计划、门禁和推进权。",
            "门禁不是让 AI 变慢，而是用低成本检查阻止高成本返工。",
            "执行完成不等于阶段通过；证据满足门禁，流程才能继续。",
            "最终验收仍然要回到原始目标，不能只接受执行者的完成声明。",
        ]))
        check("完成报告主结论正确", "丝滑不是一路不停" in report_text
              and "任务定义清楚、分工明确、门禁有效" in report_text)
        check("完成报告九项验收核对齐全", all(marker in report_text for marker in [
            "导出全部筛选结果", "中文列名正确", "空列表正常", "display_name 为空正常",
            "超过 10000 行返回 422", "复用已有筛选逻辑", "未改变原接口语义",
            "全量测试通过", "无越界修改",
        ]))

        for control_id in ("btn-start", "btn-step", "btn-jump-end", "btn-pause", "btn-continue"):
            disabled = await page.is_disabled(f"#{control_id}")
            check(f"完成后控制按钮 #{control_id} 已禁用", disabled, f"disabled={disabled}")

        # ========== G. Demo 1 / Demo 2 对照 ==========
        comparison_text = await page.inner_text("#comparison")
        check("对照区域包含两条演进路径", "模糊需求驱动" in comparison_text and "完整任务包驱动" in comparison_text)
        check("对照区域体现新版多智能体流程", all(marker in comparison_text for marker in [
            "主代理读取工程", "派发代码子代理", "门禁驳回（证据不足）", "门禁放行", "独立验收 PASS",
        ]))
        check("对照区域标注为新主结论", "丝滑不是一路不停，而是任务定义清楚、分工明确、门禁有效。"
              in comparison_text)

        # ========== H. 讲师说明：显示偏好与其他页面共用 ==========
        await page.click("#btn-toggle-guide")
        check("讲师说明可显示", await page.locator("#instructor-guide").is_visible())
        check("讲师说明显示后默认仍折叠一行", await page.locator("#instructor-guide").get_attribute("open") is None)
        await page.click("#instructor-guide summary")
        guide_text = await page.inner_text("#instructor-guide")
        check("讲师说明四部分内容齐全", all(marker in guide_text for marker in
              ["本轮给AI的命令", "当前演示什么", "固定演示步骤", "本轮结论"]))
        check("讲师说明提到主代理门禁驳回的教学重点", "驳回的是证据" in guide_text)

        await page.goto(f"{BASE}/demo")
        nav_guide_visible = await page.locator("#instructor-guide").is_visible()
        check("讲师说明偏好带入导航页", nav_guide_visible)

        # ========== I. 刷新恢复初始状态 ==========
        await page.goto(f"{BASE}/demo/codex-loop")
        refreshed_state = await js_state(page)
        check("刷新后恢复初始未运行状态", refreshed_state["currentStage"] == 0
              and refreshed_state["logBlocks"] == 0 and refreshed_state["finalHidden"] is True,
              str(refreshed_state))

        # ========== J. 不发出任何网络请求（纯前端模拟） ==========
        all_requests.clear()
        await page.click("#btn-jump-end")
        await page.wait_for_timeout(200)
        non_asset_requests = [u for u in all_requests if u != f"{BASE}/demo/codex-loop"]
        check("执行全流程不发出任何网络请求（不调用模型接口）", not non_asset_requests, str(non_asset_requests[:3]))

        # ========== K. 正式接口与原四个状态页无回归（轻量抽查）==========
        with urllib.request.urlopen(f"{BASE}/api/users/export", timeout=5) as formal:
            check("正式 /api/users/export 无回归", formal.status == 200, f"HTTP {formal.status}")
        base_resp = await page.goto(f"{BASE}/demo/users/base")
        check("原四个状态页无回归（Base 可正常打开）",
              base_resp is not None and base_resp.status == 200
              and await page.inner_text("#stage-badge") == "DEMO 00 · BASELINE")

        # ========== L. Console 与 favicon ==========
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
