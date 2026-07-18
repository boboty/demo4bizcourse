#!/usr/bin/env python3
"""课堂演示四状态浏览器冒烟验收（可选工具，不属于 pytest 基线）。

使用系统 Python 环境中已安装的 Playwright（async API）驱动真实 Chromium，
不进入 requirements.txt，不影响 .venv 与 ./scripts/test.sh。
脚本自行在 8012 端口启动/停止 uvicorn，覆盖：

- 导航页：200、四张状态卡片、入口可点击、演进路线
- 状态页框架：状态标识、返回导航、上一个/下一个状态顺序与边界禁用
- 讲师说明：默认隐藏、可展开、可整体隐藏、偏好跨页保留、六部分内容与状态一致
- Base：导出只提示待实现且不产生导出请求
- Null Failure：默认导出成功、筛选 bob 稳定失败、失败原因可解释、页面可恢复
- Page Only：导出请求携带 page/page_size、只有当前页 8 条、第二页、空值、空结果
- Final：正式接口回归（不携带分页、23 条、组合筛选）、旧链接 /demo/users 重定向
- 正式 /api/users/export 未被教学故障污染
- 每页 1366×768 首屏测量（筛选区/表头/主要操作在首屏、无横向滚动）
- 全流程无 Console error、无 /favicon.ico 请求

用法：

    python3 scripts/demo_stage_smoke_check.py
"""

from __future__ import annotations

import asyncio
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
PYTHON_BIN = ROOT_DIR / ".venv" / "bin" / "python"
PORT = 8012
BASE = f"http://127.0.0.1:{PORT}"

try:
    from playwright.async_api import TimeoutError as PlaywrightTimeoutError
    from playwright.async_api import async_playwright
except ModuleNotFoundError:
    sys.exit("未找到 Playwright：请使用已安装 Playwright 的系统 Python 运行本脚本。")

results: list[tuple[str, bool, str]] = []

STATES = ["base", "null-failure", "page-only", "final"]
BADGES = {
    "base": "DEMO 00 · BASELINE",
    "null-failure": "DEMO 01 · ONE-LINE IMPLEMENTATION",
    "page-only": "DEMO 02 · TESTS GREEN, GOAL MISSED",
    "final": "DEMO 03 · FINAL PASS",
}
SUBTITLES = {
    "base": "需求尚未实现",
    "null-failure": "功能出现，但边界失败",
    "page-only": "测试通过，但原始目标未达",
    "final": "目标、边界与证据闭环",
}
CONCLUSIONS = {
    "base": "一句话可以启动任务，但不能定义完成。",
    "null-failure": "没有写进验收标准的边界，往往会成为最先遗漏的边界。",
    "page-only": "测试通过，只能证明写进测试里的那部分通过了。",
    "final": "验证不是跑测试，而是证明结果满足原始目标。",
}
GUIDE_SECTIONS = ["本轮给AI的命令", "当前实现了什么", "当前欠缺什么", "固定演示步骤", "下一轮如何改进", "本轮结论"]


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


# ---- xlsx 解析（仅标准库，避免依赖 .venv 外的 openpyxl）----
def xlsx_row_count(path: str) -> int:
    with zipfile.ZipFile(path) as archive:
        xml = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
    return len(re.findall(r"<row[ >]", xml))


def xlsx_text_content(path: str) -> str:
    """工作表全部文本内容：openpyxl 默认写内联字符串（无 sharedStrings.xml），
    因此需要同时读取 sheet1.xml 本身，而不能只看共享字符串表。"""

    with zipfile.ZipFile(path) as archive:
        text = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
        try:
            text += archive.read("xl/sharedStrings.xml").decode("utf-8")
        except KeyError:
            pass
        return text


async def wait_rows(page, count: int) -> None:
    await page.wait_for_function(
        f"document.querySelectorAll('#user-table-body tr').length === {count}"
        " && !document.querySelector('#user-table-body').textContent.includes('正在加载')")


async def measure_first_screen(page, label: str) -> None:
    """1366×768 首屏：筛选区、表头与主要操作在首屏，无横向滚动。"""

    filter_box = await page.locator("#filter-form").bounding_box()
    header_box = await page.locator("table thead").bounding_box()
    export_box = await page.locator("#btn-export").bounding_box()
    pagination_box = await page.locator(".pagination").bounding_box()
    scroll_width = await page.evaluate("document.documentElement.scrollWidth")
    body_font = await page.evaluate("getComputedStyle(document.body).fontSize")
    check(f"{label}：首屏可见筛选区与主要操作",
          filter_box["y"] + filter_box["height"] <= 768 and export_box["y"] + export_box["height"] <= 768,
          f"筛选区底部 y={filter_box['y'] + filter_box['height']:.0f}")
    check(f"{label}：表头与分页在首屏",
          header_box["y"] + header_box["height"] <= 768 and pagination_box["y"] + pagination_box["height"] <= 768,
          f"分页底部 y={pagination_box['y'] + pagination_box['height']:.0f}")
    check(f"{label}：无横向滚动", scroll_width <= 1366, f"scrollWidth={scroll_width}")
    check(f"{label}：正文字号不低于 15px", float(body_font.replace("px", "")) >= 15, f"body {body_font}")


async def run() -> int:
    console_errors: list[str] = []
    favicon_requests: list[str] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(viewport={"width": 1366, "height": 768}, accept_downloads=True)
        page = await context.new_page()
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: console_errors.append(str(exc)))
        page.on("request", lambda req: favicon_requests.append(req.url) if "favicon" in req.url else None)

        with tempfile.TemporaryDirectory() as tmp:

            async def save_download(download, name: str) -> str:
                path = str(Path(tmp) / name)
                await download.save_as(path)
                return path

            # ========== A. 根路径与导航页 ==========
            resp = await page.goto(f"{BASE}/")
            check("根路径重定向到导航页", resp is not None and resp.status == 200 and page.url.endswith("/demo"),
                  page.url)
            resp = await page.goto(f"{BASE}/demo")
            check("导航页打开成功", resp is not None and resp.status == 200)
            check("导航页标题与副标题", "AI研发验证闭环课堂演示" in await page.inner_text("h1")
                  and "从一句模糊需求，到可以被证据证明的最终结果" in await page.inner_text(".subtitle"))
            route_text = await page.inner_text(".route-line")
            check("演进路线四阶段", all(phase in route_text for phase in
                  ["需求未实现", "功能出现但边界失败", "测试通过但目标未达", "目标与证据闭环"]), route_text[:60])
            hrefs = await page.locator(".card a.card-enter").evaluate_all("els => els.map(e => e.getAttribute('href'))")
            check("导航页四个入口存在", hrefs == [f"/demo/users/{s}" for s in STATES], str(hrefs))
            card_text = await page.inner_text(".cards")
            check("导航页卡片状态名正确", all(name in card_text for name in
                  ["00 · Baseline", "01 · One-line Implementation", "02 · Tests Green, Goal Missed", "03 · Final Pass"]))
            nav_text = await page.inner_text("main")
            check("导航页清楚区分 Demo 1 与 Demo 2", "Demo 1 · 从模糊需求到可验证任务" in nav_text
                  and "Demo 2 · 完整任务包驱动研发闭环" in nav_text)
            codex_href = await page.locator(".codex-card a.codex-enter").get_attribute("href")
            check("导航页 Demo 2 入口存在且指向 /demo/codex-loop", codex_href == "/demo/codex-loop", codex_href)
            nav_scroll_height = await page.evaluate("document.documentElement.scrollHeight")
            check("导航页 1366×768 内无需滚动即可看到两个 Demo 区域", nav_scroll_height <= 768,
                  f"scrollHeight={nav_scroll_height}")
            check("导航页讲师说明默认隐藏", await page.locator("#instructor-guide").is_hidden())
            await page.click("#btn-toggle-guide")
            check("导航页讲师说明可显示", await page.locator("#instructor-guide").is_visible()
                  and await page.inner_text("#btn-toggle-guide") == "隐藏讲师说明")
            await page.click("#btn-toggle-guide")
            check("导航页讲师说明可隐藏", await page.locator("#instructor-guide").is_hidden())

            # 卡片可点击：进入 00
            await page.click(".card a.card-enter >> nth=0")
            await wait_rows(page, 8)
            check("点击卡片进入 00 Base", page.url.endswith("/demo/users/base")
                  and await page.inner_text("#stage-badge") == BADGES["base"])
            await page.click(".nav-home")
            check("返回演示导航可用", page.url.endswith("/demo"), page.url)

            # Demo 2 入口可点击进入
            await page.click(".codex-card a.codex-enter")
            check("点击 Demo 2 入口进入 /demo/codex-loop", page.url.endswith("/demo/codex-loop"), page.url)
            await page.click(".nav-home >> nth=0")
            check("Demo 2 页返回演示导航可用", page.url.endswith("/demo"), page.url)

            # ========== B. 状态页框架（逐状态）==========
            for index, state_key in enumerate(STATES):
                await page.goto(f"{BASE}/demo/users/{state_key}")
                await page.evaluate("sessionStorage.clear()")
                await page.reload()
                await wait_rows(page, 8)
                check(f"[{state_key}] 状态标识与中英文名称",
                      await page.inner_text("#stage-badge") == BADGES[state_key]
                      and SUBTITLES[state_key] in await page.inner_text("#stage-subtitle"),
                      await page.inner_text("#stage-badge"))
                check(f"[{state_key}] 默认加载 8 条共 23 条",
                      "第 1 页 / 共 3 页 ｜ 共 23 条" in await page.inner_text("#page-info"),
                      await page.inner_text("#page-info"))

                prev_disabled = await page.locator("#nav-prev").is_disabled()
                next_disabled = await page.locator("#nav-next").is_disabled()
                boundary_ok = (prev_disabled if index == 0 else not prev_disabled) and \
                              (next_disabled if index == len(STATES) - 1 else not next_disabled)
                check(f"[{state_key}] 上一个/下一个状态边界禁用正确", boundary_ok,
                      f"prev disabled={prev_disabled}, next disabled={next_disabled}")

                # 讲师说明：默认隐藏 → 显示 → 折叠一行 → 展开六部分 → 文案不串页
                check(f"[{state_key}] 讲师说明默认隐藏", await page.locator("#instructor-guide").is_hidden())
                await page.click("#btn-toggle-guide")
                guide_visible = await page.locator("#instructor-guide").is_visible()
                body_hidden = await page.locator("#guide-body").is_hidden()
                check(f"[{state_key}] 讲师说明显示且默认折叠一行", guide_visible and body_hidden)
                await page.click("#instructor-guide summary")
                headings = await page.locator("#guide-body h2").all_inner_texts()
                guide_text = await page.inner_text("#guide-body")
                others = [c for k, c in CONCLUSIONS.items() if k != state_key]
                check(f"[{state_key}] 说明六部分齐全", headings == GUIDE_SECTIONS, "｜".join(headings))
                check(f"[{state_key}] 说明内容与状态一致且不串页",
                      CONCLUSIONS[state_key] in guide_text and not any(c in guide_text for c in others))
                await page.click("#instructor-guide summary")  # 收起，恢复默认折叠一行，供首屏测量

                # 键盘操作：焦点 + 回车切换讲师说明
                await page.focus("#btn-toggle-guide")
                await page.keyboard.press("Enter")
                check(f"[{state_key}] 讲师说明支持键盘切换", await page.locator("#instructor-guide").is_hidden())
                await page.click("#btn-toggle-guide")  # 保持显示（默认折叠一行），验证跨页保留

                # 首屏测量代表课堂默认状态：说明已显示但折叠为一行，不应影响首屏
                await measure_first_screen(page, f"[{state_key}] 1366×768")

            # 偏好跨页保留：上一循环结束时各页均处于“显示”
            await page.goto(f"{BASE}/demo/users/base")
            await wait_rows(page, 8)
            check("讲师说明偏好跨状态页保留", await page.locator("#instructor-guide").is_visible())
            await page.click("#btn-toggle-guide")
            guide_display = await page.evaluate("getComputedStyle(document.getElementById('instructor-guide')).display")
            check("隐藏讲师说明后不留占位空白", guide_display == "none", f"display={guide_display}")
            await page.evaluate("sessionStorage.clear()")
            await page.reload()
            await wait_rows(page, 8)

            # 上一个/下一个状态顺序：base → null-failure → page-only → final
            await page.click("#nav-next")
            await wait_rows(page, 8)
            ok_step1 = page.url.endswith("/demo/users/null-failure")
            await page.click("#nav-next")
            await wait_rows(page, 8)
            ok_step2 = page.url.endswith("/demo/users/page-only")
            await page.click("#nav-prev")
            await wait_rows(page, 8)
            ok_step3 = page.url.endswith("/demo/users/null-failure")
            await page.click("#nav-prev")
            await wait_rows(page, 8)
            check("上一个/下一个状态顺序正确", ok_step1 and ok_step2 and ok_step3
                  and page.url.endswith("/demo/users/base"), page.url)

            # ========== C. Base：导出只提示待实现 ==========
            await page.goto(f"{BASE}/demo/users/base")
            await wait_rows(page, 8)
            await page.fill("#filter-username", "chen")
            await page.select_option("#filter-status", "active")
            await page.click("#btn-search")
            await wait_rows(page, 2)
            check("[base] 组合筛选正常", "共 2 条" in await page.inner_text("#page-info"),
                  await page.inner_text("#page-info"))
            export_requests: list[str] = []
            page.on("request", lambda req: export_requests.append(req.url) if "export" in req.url else None)
            await page.click("#btn-export")
            await page.wait_for_selector("#export-status.info", timeout=5000)
            info_text = await page.inner_text("#export-status")
            check("[base] 点击导出只提示待实现", "待实现" in info_text and "需求入口" in info_text, info_text)
            check("[base] 未产生任何导出网络请求", not export_requests, str(export_requests))
            check("[base] 请求详情说明未发起导出",
                  "未发起" in await page.text_content("#info-export-url"))
            await page.click("#btn-reset")
            await wait_rows(page, 8)

            # ========== D. Null Failure：固定复现 ==========
            await page.goto(f"{BASE}/demo/users/null-failure")
            await wait_rows(page, 8)
            async with page.expect_download() as dl_info:
                await page.click("#btn-export")
            path = await save_download(await dl_info.value, "null_default.xlsx")
            check("[null-failure] 默认导出成功", xlsx_row_count(path) == 24,
                  f"xlsx 行数 {xlsx_row_count(path)}（含表头）")
            check("[null-failure] 调用教学专用接口",
                  "/api/demo/users/export/null-failure" in await page.text_content("#info-export-url"),
                  await page.text_content("#info-export-url"))

            await page.fill("#filter-username", "bob")
            await page.click("#btn-search")
            await wait_rows(page, 1)
            name_cell = await page.inner_text("#user-table-body tr td:nth-child(3)")
            check("[null-failure] bob 查询成功且姓名为空值占位", name_cell == "—", f"姓名列：{name_cell!r}")
            try:
                async with page.expect_download(timeout=2000) as _:
                    await page.click("#btn-export")
                bob_downloaded = True
            except PlaywrightTimeoutError:
                bob_downloaded = False
            await page.wait_for_selector("#export-status.error", timeout=5000)
            err_text = await page.inner_text("#export-status")
            check("[null-failure] bob 导出稳定失败且原因可解释",
                  not bob_downloaded and "空值" in err_text and "None" in err_text and "strip" in err_text,
                  err_text[:80])
            # 页面可恢复
            await page.click("#btn-reset")
            await wait_rows(page, 8)
            check("[null-failure] 失败后页面恢复操作",
                  "查询成功" in await page.inner_text("#list-status"))
            # 正式接口不受影响（页面外直接请求）
            with urllib.request.urlopen(f"{BASE}/api/users/export", timeout=5) as formal:
                formal_bytes = formal.read()
            formal_tmp = str(Path(tmp) / "formal.xlsx")
            Path(formal_tmp).write_bytes(formal_bytes)
            check("[null-failure] 正式 /api/users/export 不受影响",
                  formal.status == 200 and xlsx_row_count(formal_tmp) == 24,
                  f"HTTP {formal.status}，行数 {xlsx_row_count(formal_tmp)}")

            # ========== E. Page Only：固定复现 ==========
            await page.goto(f"{BASE}/demo/users/page-only")
            await wait_rows(page, 8)
            check("[page-only] 页面显示共23条每页8条",
                  "共 23 条" in await page.inner_text("#page-info")
                  and "每页 8 条" in await page.inner_text("#filter-summary"))
            export_urls: list[str] = []
            page.on("request", lambda req: export_urls.append(req.url) if "export" in req.url else None)
            async with page.expect_download() as dl_info:
                await page.click("#btn-export")
            path = await save_download(await dl_info.value, "page1.xlsx")
            url = export_urls[-1] if export_urls else ""
            check("[page-only] 导出请求携带 page=1&page_size=8",
                  "/api/demo/users/export/page-only?page=1&page_size=8" in url, url)
            check("[page-only] Excel 只有当前页 8 条", xlsx_row_count(path) == 9,
                  f"xlsx 数据行 {xlsx_row_count(path) - 1}")
            check("[page-only] 页面不报错",
                  "导出成功" in await page.inner_text("#export-status"))
            await page.click("#btn-next")
            await page.wait_for_function("document.querySelector('#page-info').textContent.includes('第 2 页')")
            async with page.expect_download() as dl_info:
                await page.click("#btn-export")
            path = await save_download(await dl_info.value, "page2.xlsx")
            url = export_urls[-1] if export_urls else ""
            strings = xlsx_text_content(path)
            check("[page-only] 第二页导出只含第二页数据",
                  "page=2" in url and xlsx_row_count(path) == 9
                  and "iris" in strings and "alice" not in strings,
                  f"url={url.split('?')[-1]}，数据行 {xlsx_row_count(path) - 1}")
            await page.fill("#filter-username", "zzz_no_such_user")
            await page.click("#btn-search")
            await page.wait_for_function(
                "document.querySelector('#user-table-body').textContent.includes('没有符合当前筛选条件的用户')")
            async with page.expect_download() as dl_info:
                await page.click("#btn-export")
            path = await save_download(await dl_info.value, "empty.xlsx")
            check("[page-only] 空结果导出为只有表头的有效文件", xlsx_row_count(path) == 1)
            await page.click("#btn-reset")
            await wait_rows(page, 8)
            await page.fill("#filter-username", "bob")
            await page.click("#btn-search")
            await wait_rows(page, 1)
            async with page.expect_download() as dl_info:
                await page.click("#btn-export")
            path = await save_download(await dl_info.value, "bob_page.xlsx")
            check("[page-only] 空值用户导出正常", xlsx_row_count(path) == 2)
            await page.click("#btn-reset")
            await wait_rows(page, 8)

            # ========== F. Final：正式逻辑回归 ==========
            await page.goto(f"{BASE}/demo/users/final")
            await wait_rows(page, 8)
            final_export_urls: list[str] = []
            page.on("request", lambda req: final_export_urls.append(req.url)
                    if "/api/users/export" in req.url else None)
            async with page.expect_download() as dl_info:
                await page.click("#btn-export")
            path = await save_download(await dl_info.value, "final_default.xlsx")
            url = final_export_urls[-1] if final_export_urls else ""
            check("[final] 默认导出23条且不携带分页",
                  xlsx_row_count(path) == 24 and "page=" not in url and "page_size=" not in url,
                  f"url={url}，数据行 {xlsx_row_count(path) - 1}")
            await page.fill("#filter-username", "chen")
            await page.select_option("#filter-status", "active")
            await page.click("#btn-search")
            await wait_rows(page, 2)
            async with page.expect_download() as dl_info:
                await page.click("#btn-export")
            path = await save_download(await dl_info.value, "final_filter.xlsx")
            url = final_export_urls[-1] if final_export_urls else ""
            strings = xlsx_text_content(path)
            check("[final] 组合筛选导出保留筛选、不含分页",
                  "username=chen" in url and "status=active" in url and "page=" not in url
                  and xlsx_row_count(path) == 3 and "rachel.chen" not in strings,
                  f"url={url.split('?')[-1]}，数据行 {xlsx_row_count(path) - 1}")
            # 旧链接兼容
            resp = await page.goto(f"{BASE}/demo/users")
            await wait_rows(page, 8)
            check("旧链接 /demo/users 重定向到 final",
                  resp is not None and resp.status == 200 and page.url.endswith("/demo/users/final")
                  and await page.inner_text("#stage-badge") == BADGES["final"], page.url)

            # ========== G. Console 与 favicon ==========
            # Null Failure 状态按设计稳定返回 HTTP 500（教学故障），Chromium 会对失败的
            # fetch 请求自动记录一条 "Failed to load resource...500" 的浏览器级日志，
            # 这不是页面代码抛出的异常（页面本身从不调用 console.*）。该状态之外的
            # 三个状态与正式接口全程不应出现任何 500，故只在此排除该条已知预期日志。
            unexpected_errors = [e for e in console_errors if "500" not in e]
            check("全流程无非预期 Console error（Null Failure 的预期500日志除外）",
                  not unexpected_errors, "; ".join(unexpected_errors[:3]))
            check("Null Failure 的预期500日志确实存在且仅此一类",
                  len(console_errors) - len(unexpected_errors) >= 1,
                  f"共 {len(console_errors)} 条，其中 500 相关 {len(console_errors) - len(unexpected_errors)} 条")
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
