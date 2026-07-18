#!/usr/bin/env python3
"""课堂演示教学状态检查脚本。

用法（可直接用系统 python3，脚本会自动切换到项目 .venv 执行）：

    python3 scripts/demo_stage_checks.py page-only   # Stage 2 局部检查
    python3 scripts/demo_stage_checks.py final       # Final 完整验证

说明：

- page-only 是 Stage 2（测试通过但目标未达）的局部检查，只验证本阶段
  写进测试里的范围，不是完整验收；
- final 是最终状态的完整验证，覆盖目标、边界与导出范围；
- 页面真实操作链路另见 scripts/demo_smoke_check.py 与
  scripts/demo_stage_smoke_check.py。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
VENV_PYTHON = ROOT_DIR / ".venv" / "bin" / "python"

# 允许直接用系统 python3 调用：切到项目 .venv（fastapi/openpyxl 在其中）。
if VENV_PYTHON.exists() and Path(sys.executable).resolve() != VENV_PYTHON.resolve():
    os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]])

sys.path.insert(0, str(ROOT_DIR))

from io import BytesIO  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402
from openpyxl import load_workbook  # noqa: E402

from app.main import create_app  # noqa: E402
from app.services.user_export_service import USER_EXPORT_HEADERS  # noqa: E402

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'} {name}" + (f" — {detail}" if detail else ""), flush=True)


def read_rows(content: bytes) -> list[tuple[object, ...]]:
    worksheet = load_workbook(BytesIO(content), read_only=True).active
    return list(worksheet.values)


def run_page_only() -> int:
    """Stage 2 局部检查：只覆盖本阶段写进测试的范围，不是完整验收。"""

    print("Stage 2 局部检查（page-only 教学状态）")
    print("范围：能导出、文件合法、表头正确、空值处理、当前页数据；不代表完整验收。")
    print()

    with TestClient(create_app()) as client:
        response = client.get("/api/demo/users/export/page-only", params={"page": 1, "page_size": 8})
        check("文件返回200", response.status_code == 200, f"HTTP {response.status_code}")

        rows: list[tuple[object, ...]] = []
        try:
            rows = read_rows(response.content)
            check("文件为有效xlsx", True, "openpyxl 可正常读取")
        except Exception as exc:  # noqa: BLE001 - 课堂检查需如实报告任何解析失败
            check("文件为有效xlsx", False, str(exc))

        if rows:
            check("中文表头正确", rows[0] == USER_EXPORT_HEADERS, f"表头：{rows[0]}")
            data_ids = [row[0] for row in rows[1:]]
            check("当前页数据存在", data_ids == list(range(1, 9)), f"当前页 ID：{data_ids}")
        else:
            check("中文表头正确", False, "无任何行")
            check("当前页数据存在", False, "无任何行")

        null_response = client.get("/api/demo/users/export/page-only", params={"username": "bob"})
        null_rows = read_rows(null_response.content) if null_response.status_code == 200 else []
        check(
            "空值处理正常",
            null_response.status_code == 200 and len(null_rows) == 2 and null_rows[1][2] is None,
            "bob 的空显示名称导出为空单元格，不报错",
        )

    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n{passed}/{len(results)} PASS")
    print()
    print("注意：这是 Stage 2 局部检查，故意没有检查：")
    print("- 导出总数是否等于筛选总数；")
    print("- 请求是否包含 page/page_size；")
    print("- 第二页之外的数据是否存在。")
    return 0 if passed == len(results) else 1


def run_final() -> int:
    """Final 完整验证：目标、边界与导出范围。"""

    print("Final 完整验证（final 教学状态，正式 /api/users/export）")
    print()

    with TestClient(create_app()) as client:
        default_response = client.get("/api/users/export")
        default_rows = read_rows(default_response.content)
        check("默认导出23条", len(default_rows) == 24, f"数据行：{len(default_rows) - 1}")
        check("文件可由openpyxl读取", default_rows[0] == USER_EXPORT_HEADERS, "表头与顺序正确")

        username_rows = read_rows(client.get("/api/users/export", params={"username": "chen"}).content)
        check("username筛选导出正确", [row[1] for row in username_rows[1:]]
              == ["helen.chen", "mia.chen", "rachel.chen"], f"导出 {len(username_rows) - 1} 条")

        status_rows = read_rows(client.get("/api/users/export", params={"status": "active"}).content)
        check("status筛选导出正确", len(status_rows) == 16
              and all(row[4] == "active" for row in status_rows[1:]), f"导出 {len(status_rows) - 1} 条")

        combo_rows = read_rows(
            client.get("/api/users/export", params={"username": "chen", "status": "active"}).content
        )
        check("组合筛选导出正确", [row[1] for row in combo_rows[1:]] == ["helen.chen", "mia.chen"],
              f"导出 {len(combo_rows) - 1} 条")

        null_rows = read_rows(client.get("/api/users/export", params={"username": "bob"}).content)
        check("空值导出正常", len(null_rows) == 2 and null_rows[1][2] is None, "空显示名称为空单元格")

        empty_response = client.get("/api/users/export", params={"username": "zzz_no_such_user"})
        check("空结果导出有效", empty_response.status_code == 200
              and read_rows(empty_response.content) == [USER_EXPORT_HEADERS], "只有表头的有效xlsx")

        # 导出范围 = 筛选全集：active 共 15 条，超过列表每页 8 条，导出必须全部包含。
        list_all = client.get("/api/users", params={"status": "active", "page": 1, "page_size": 100})
        expected_ids = [item["id"] for item in list_all.json()["items"]]
        export_ids = [row[0] for row in status_rows[1:]]
        check("导出不携带page/page_size（导出范围=筛选全集）",
              export_ids == expected_ids and len(export_ids) == 15,
              f"导出 {len(export_ids)} 条，与筛选全集一致")

    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n{passed}/{len(results)} PASS")
    print("页面真实操作链路另见 scripts/demo_smoke_check.py 与 scripts/demo_stage_smoke_check.py。")
    return 0 if passed == len(results) else 1


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in ("page-only", "final"):
        print(__doc__)
        return 2
    if sys.argv[1] == "page-only":
        return run_page_only()
    return run_final()


if __name__ == "__main__":
    sys.exit(main())
