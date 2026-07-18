#!/usr/bin/env python3
"""课堂 Demo 页面浏览器冒烟验收（可选工具，不属于 pytest 基线）。

使用系统 Python 环境中已安装的 Playwright（async API）驱动真实 Chromium，
不进入 requirements.txt，不影响 .venv 与 ./scripts/test.sh。
脚本自行在 8010 端口启动/停止 uvicorn，覆盖：

- 页面打开成功、默认加载数据（每页 8 条、共 3 页）
- 1366×768 首屏布局测量（筛选区/表格可见行数/分页位置）
- 用户名筛选、状态筛选、筛选后回到第一页
- 翻页后保留筛选条件
- 空结果提示
- 列表 API 失败后保留上一次成功页（校验具体记录 ID），恢复后可再次翻页
- 修改筛选后列表失败：筛选输入、摘要、表格记录、分页与导出口径整体恢复
- 真实并发：async route 回调中非阻塞挂起 alice 请求，在其在途期间发起 bob；
  断言事件等待结果、网络记录中 alice 被取消（或旧响应晚于 bob）。
  注：加载期间查询按钮按需求禁用，Chromium 会阻断回车的隐式提交，
  因此第二次查询用 requestSubmit() 触发，以制造真实重叠请求。
- 导出请求携带当前筛选且不携带分页参数，并触发 users.xlsx 下载
- 无 Console error、无 /favicon.ico 请求

用法：

    python3 scripts/demo_smoke_check.py
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
PYTHON_BIN = ROOT_DIR / ".venv" / "bin" / "python"
PORT = 8010
BASE = f"http://127.0.0.1:{PORT}"

try:
    from playwright.async_api import async_playwright
except ModuleNotFoundError:
    sys.exit("未找到 Playwright：请使用已安装 Playwright 的系统 Python 运行本脚本。")

results: list[tuple[str, bool, str]] = []


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


async def first_col_ids(page) -> list[str]:
    """当前表格第一列（ID）文本，用于校验失败后表格内容未被改动。"""

    return await page.locator("#user-table-body tr td:nth-child(1)").all_inner_texts()


async def wait_event(name: str, event: asyncio.Event, timeout: float) -> bool:
    """等待事件并返回是否等到；超时返回 False 而不是静默继续。"""

    try:
        await asyncio.wait_for(event.wait(), timeout=timeout)
        return True
    except asyncio.TimeoutError:
        print(f"  [WARN] 等待事件超时（{timeout}s）：{name}", flush=True)
        return False


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

        rows_8 = "document.querySelectorAll('#user-table-body tr').length === 8"
        page2 = "document.querySelector('#page-info').textContent.includes('第 2 页')"

        # 1. 打开页面 + 默认加载
        resp = await page.goto(f"{BASE}/demo/users")
        await page.wait_for_selector("#user-table-body tr td", timeout=5000)
        await page.wait_for_function(rows_8)
        check("页面打开成功", resp is not None and resp.status == 200)
        rows = page.locator("#user-table-body tr")
        check("默认加载数据", await rows.count() == 8 and "共 23 条" in await page.inner_text("#page-info"),
              await page.inner_text("#page-info"))

        # 2. 1366×768 首屏测量
        filter_box = await page.locator("#filter-form").bounding_box()
        pagination_box = await page.locator(".pagination").bounding_box()
        visible_rows = 0
        for i in range(await rows.count()):
            b = await rows.nth(i).bounding_box()
            if b and b["y"] >= 0 and b["y"] + b["height"] <= 768:
                visible_rows += 1
        body_font = await page.evaluate("getComputedStyle(document.body).fontSize")
        check("首屏可见筛选区", filter_box["y"] + filter_box["height"] <= 768,
              f"筛选区底部 y={filter_box['y'] + filter_box['height']:.0f}")
        check("首屏可见至少 5 行数据", visible_rows >= 5, f"完整可见 {visible_rows} 行")
        check("分页位于首屏", pagination_box["y"] + pagination_box["height"] <= 768,
              f"分页底部 y={pagination_box['y'] + pagination_box['height']:.0f}")
        check("正文字号不低于 15px", float(body_font.replace("px", "")) >= 15, f"body {body_font}")

        # 3. 用户名筛选
        await page.fill("#filter-username", "chen")
        await page.click("#btn-search")
        await page.wait_for_function("document.querySelectorAll('#user-table-body tr').length === 3")
        check("用户名筛选 chen", "共 3 条" in await page.inner_text("#page-info")
              and "用户名 chen" in await page.inner_text("#filter-summary"))

        # 4. 状态筛选 + 筛选后回到第一页（先翻到第 2 页再改筛选）
        await page.click("#btn-reset")
        await page.wait_for_function(rows_8)
        await page.click("#btn-next")
        await page.wait_for_function(page2)
        await page.select_option("#filter-status", "active")
        await page.click("#btn-search")
        await page.wait_for_function("document.querySelector('#page-info').textContent.includes('第 1 页')")
        check("筛选后回到第一页", "第 1 页 / 共 2 页 ｜ 共 15 条" in await page.inner_text("#page-info"),
              await page.inner_text("#page-info"))

        # 5. 翻页后保留筛选条件
        await page.click("#btn-next")
        await page.wait_for_function(page2)
        summary = await page.inner_text("#filter-summary")
        statuses = await page.locator("#user-table-body tr td:nth-child(5)").all_inner_texts()
        check("翻页后保留 active 筛选", "状态 active" in summary and "第 2 页" in summary
              and len(statuses) == 7 and set(statuses) == {"active"},
              f"摘要: {summary.strip()}")

        # 6. 空结果
        await page.fill("#filter-username", "zzz_no_such_user")
        await page.click("#btn-search")
        await page.wait_for_function(
            "document.querySelector('#user-table-body').textContent.includes('没有符合当前筛选条件的用户')")
        check("空结果提示", "没有符合当前筛选条件的用户" in await page.inner_text("#list-status"))

        # 7. 翻页失败：保留上一次成功页（含具体记录），恢复后可再次翻页
        await page.click("#btn-reset")
        await page.wait_for_function(rows_8)
        ids_before = await first_col_ids(page)

        async def abort_page2(route):
            await route.abort()

        await page.route("**/api/users?page=2&page_size=8", abort_page2)
        await page.click("#btn-next")
        await page.wait_for_selector("#list-status.error", timeout=5000)
        ids_after_fail = await first_col_ids(page)
        page_info = await page.inner_text("#page-info")
        check("失败后保留上一次成功页",
              ids_after_fail == ids_before == [str(i) for i in range(1, 9)]
              and "第 1 页 / 共 3 页 ｜ 共 23 条" in page_info,
              f"IDs={ids_after_fail} page-info: {page_info}")
        check("请求详情如实反映网络错误",
              "无响应（网络错误）" in await page.text_content("#info-list-status")
              and "请求失败" in await page.text_content("#info-list-count"),
              await page.text_content("#info-list-status"))
        await page.unroute("**/api/users?page=2&page_size=8")
        await page.click("#btn-next")
        await page.wait_for_function(page2)
        check("恢复后再次翻页成功", "第 2 页 / 共 3 页" in await page.inner_text("#page-info"))

        # 7b. 修改筛选后列表失败：筛选输入、摘要、表格、分页与导出口径整体恢复
        await page.click("#btn-reset")
        # 必须等到第 1 页数据真正渲染（此前表格停留的第 2 页同样满足 8 行条件）
        await page.wait_for_function(
            "document.querySelectorAll('#user-table-body tr').length === 8"
            " && document.querySelector('#user-table-body tr td').textContent === '1'")
        ids_before = await first_col_ids(page)

        async def fail_zzz(route):
            if "username=zzz_fail" in route.request.url:
                await route.abort()
            else:
                await route.continue_()

        await page.route("**/api/users?**", fail_zzz)
        await page.fill("#filter-username", "zzz_fail")
        await page.click("#btn-search")
        await page.wait_for_selector("#list-status.error", timeout=5000)
        summary = await page.inner_text("#filter-summary")
        parts = {
            "用户名输入恢复": await page.input_value("#filter-username") == "",
            "状态输入恢复": await page.input_value("#filter-status") == "",
            "摘要恢复": "用户名 全部" in summary and "状态 全部" in summary and "第 1 页" in summary,
            "表格记录不变": await first_col_ids(page) == ids_before,
            "分页信息不变": "第 1 页 / 共 3 页 ｜ 共 23 条" in await page.inner_text("#page-info"),
        }
        check("筛选失败后整体恢复上一次成功口径", all(parts.values()),
              ", ".join(f"{k}:{'OK' if v else 'FAIL'}" for k, v in parts.items()))
        export_urls_fail: list[str] = []
        page.on("request",
                lambda req: export_urls_fail.append(req.url) if "/api/users/export" in req.url else None)
        async with page.expect_download():
            await page.click("#btn-export")
        export_after_fail = export_urls_fail[-1] if export_urls_fail else ""
        check("失败后导出口径随之恢复", export_after_fail == f"{BASE}/api/users/export", export_after_fail)
        await page.unroute("**/api/users?**")

        # 8. 真实并发：非阻塞挂起 alice 请求，在其在途期间发起 bob
        await page.click("#btn-reset")
        await page.wait_for_function(rows_8)

        alice_in_flight = asyncio.Event()
        alice_release = asyncio.Event()
        alice_handled = asyncio.Event()
        gate_timed_out: list[bool] = []
        netlog: list[tuple[str, str, float]] = []

        async def gate_alice(route):
            if "username=alice" not in route.request.url:
                await route.continue_()
                return
            alice_in_flight.set()
            try:
                await asyncio.wait_for(alice_release.wait(), timeout=10)
            except asyncio.TimeoutError:
                gate_timed_out.append(True)  # 挂起未被测试放行，属测试失效
            try:
                await route.continue_()
            except Exception:
                pass  # 请求已被页面 AbortController 取消，属预期行为
            finally:
                alice_handled.set()

        def log_failed(req):
            if "username=" in req.url and "/api/users?" in req.url:
                netlog.append(("failed:" + str(req.failure), req.url, time.monotonic()))

        def log_response(resp):
            if "username=" in resp.url and "/api/users?" in resp.url and "export" not in resp.url:
                netlog.append(("response:" + str(resp.status), resp.url, time.monotonic()))

        page.on("requestfailed", log_failed)
        page.on("response", log_response)
        await page.route("**/api/users?**", gate_alice)

        await page.fill("#filter-username", "alice")
        # 等待上一次加载彻底完成（查询按钮重新可用），否则 Chromium 会阻断回车的隐式提交
        await page.wait_for_function("!document.querySelector('#btn-search').disabled")
        await page.press("#filter-username", "Enter")
        in_flight_ok = await wait_event("alice 请求在途", alice_in_flight, timeout=5)
        check("alice 慢请求确实在途", in_flight_ok)

        # alice 在途期间查询按钮处于禁用态，回车隐式提交被浏览器阻断；
        # 用 requestSubmit() 触发第二次查询，制造真实的重叠请求
        await page.fill("#filter-username", "bob")
        await page.evaluate("document.getElementById('filter-form').requestSubmit()")
        await page.wait_for_function(
            "document.querySelectorAll('#user-table-body tr').length === 1"
            " && document.querySelector('#user-table-body').textContent.includes('bob')")
        alice_release.set()  # 在 bob 结果已渲染后才放行 alice
        handled_ok = await wait_event("alice 路由处理完结", alice_handled, timeout=5)
        await page.wait_for_load_state("networkidle")

        final_text = await page.inner_text("#user-table-body")
        check("并发查询只保留最后结果",
              "bob" in final_text and "alice" not in final_text
              and "用户名 bob" in await page.inner_text("#filter-summary")
              and "error" not in (await page.get_attribute("#list-status", "class") or ""),
              f"状态行: {await page.inner_text('#list-status')!r}")

        bob_resp_at = next((t for kind, url, t in netlog
                            if kind.startswith("response") and "username=bob" in url), None)
        alice_aborted = any(kind.startswith("failed") and "ABORTED" in kind and "username=alice" in url
                            for kind, url, _ in netlog)
        alice_resp_at = next((t for kind, url, t in netlog
                              if kind.startswith("response") and "username=alice" in url), None)
        race_evidence = alice_aborted or (alice_resp_at is not None and bob_resp_at is not None
                                          and alice_resp_at > bob_resp_at)
        check("alice 被取消或旧响应晚于 bob",
              handled_ok and not gate_timed_out and race_evidence,
              "; ".join(f"{kind} {url.split('?')[-1]}" for kind, url, _ in netlog) or "无网络记录")
        await page.unroute("**/api/users?**")

        # 9. 导出参数：携带筛选、不携带分页，且触发 users.xlsx 下载
        export_urls: list[str] = []
        page.on("request", lambda req: export_urls.append(req.url) if "/api/users/export" in req.url else None)
        await page.fill("#filter-username", "chen")
        await page.select_option("#filter-status", "active")
        await page.click("#btn-search")
        await page.wait_for_function("document.querySelectorAll('#user-table-body tr').length === 2")
        async with page.expect_download() as download_info:
            await page.click("#btn-export")
        download = await download_info.value
        url = export_urls[-1] if export_urls else ""
        check("导出携带当前筛选、不含分页", "username=chen" in url and "status=active" in url
              and "page=" not in url and "page_size=" not in url, url)
        check("导出触发下载", download.suggested_filename == "users.xlsx", download.suggested_filename)

        # 10. Console 与 favicon（此前人为制造的 route.abort 不算）
        console_errors.clear()
        await page.goto(f"{BASE}/demo/users")
        await page.wait_for_function(rows_8)
        await page.click("#btn-next")
        await page.wait_for_function(page2)
        check("正常操作无 Console error", not console_errors, "; ".join(console_errors[:3]))
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
