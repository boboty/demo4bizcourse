#!/usr/bin/env python3
"""D1 的工作区外业务验收器。

这个文件只由讲师侧脚本调用，绝不复制到 A/B 执行工作区。
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "instructor" / "baselines" / "demo12-financing"
ALLOWED_CHANGED_FILES = {
    "app/main.py",
    "app/financing/service.py",
    "static/index.html",
    "docs/api.md",
    "tests/test_financing_baseline.py",
}
IGNORED_PARTS = {".pytest_cache", "__pycache__", ".d1-harness"}


def source_files(root: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if path.is_file() and not IGNORED_PARTS.intersection(path.parts):
            files[str(relative)] = path.read_bytes()
    return files


def changed_paths(workspace: Path) -> list[str]:
    baseline = source_files(BASELINE)
    current = source_files(workspace)
    return sorted(
        path
        for path in baseline.keys() | current.keys()
        if baseline.get(path) != current.get(path)
    )


def load_client(workspace: Path):
    for name in tuple(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]
    sys.path.insert(0, str(workspace))
    try:
        app = importlib.import_module("app.main").app
        return importlib.import_module("fastapi.testclient").TestClient(app)
    finally:
        sys.path.pop(0)


def validate(workspace: Path) -> tuple[list[dict[str, object]], list[str]]:
    client = load_client(workspace)
    checks: list[dict[str, object]] = []
    problems: list[str] = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        checks.append({"name": name, "passed": passed, "detail": detail})
        if not passed:
            problems.append(name)

    response = client.get("/api/financing-applications?customer_name=华星", headers={"X-User": "alice"})
    body = response.json() if response.status_code == 200 else {}
    check("客户名称模糊筛选", response.status_code == 200 and body.get("total") == 2 and all("华星" in item["customer_name"] for item in body.get("items", [])))

    response = client.get("/api/financing-applications?status=APPROVED", headers={"X-User": "alice"})
    body = response.json() if response.status_code == 200 else {}
    check("融资状态精确筛选", response.status_code == 200 and body.get("total") == 2 and all(item["status"] == "APPROVED" for item in body.get("items", [])))

    response = client.get("/api/financing-applications?customer_name=华星&status=APPROVED", headers={"X-User": "alice"})
    check("多条件筛选", response.status_code == 200 and response.json().get("total") == 1)
    response = client.get("/api/financing-applications?customer_name=不存在", headers={"X-User": "alice"})
    check("空结果", response.status_code == 200 and response.json().get("total") == 0)

    response = client.get("/api/financing-applications?customer_name=南湾", headers={"X-User": "alice"})
    check("数据权限不被绕过", response.status_code == 200 and response.json().get("total") == 0)

    response = client.post(
        "/api/financing-applications/export?customer_name=华星&status=APPROVED",
        headers={"X-User": "alice"},
    )
    check("导出任务入口", response.status_code in (200, 202), f"HTTP {response.status_code}")
    export = response.json() if response.status_code in (200, 202) else {}
    job_id = export.get("id") or export.get("job_id")
    check("导出返回任务标识", bool(job_id))
    if job_id:
        job_response = client.get(f"/api/export-jobs/{job_id}")
        payload = job_response.json().get("payload", {}) if job_response.status_code == 200 else {}
        check("导出使用既有异步队列", job_response.status_code == 200)
        check("导出保留筛选条件和权限范围", payload.get("customer_name") == "华星" and payload.get("status") == "APPROVED" and payload.get("user") == "alice")
        check("导出字段严格正确", payload.get("fields") == ["id", "customer_name", "status", "amount"])

    html = (workspace / "static" / "index.html").read_text(encoding="utf-8")
    check("前端客户名称筛选能力", "客户名称" in html and "customer_name" in html and "/api/financing-applications" in html)
    check("前端融资状态筛选能力", ("融资状态" in html or "全部状态" in html) and "status" in html and "APPROVED" in html)
    check("前端导出能力", "导出" in html and "/api/financing-applications/export" in html and "POST" in html)

    changed = changed_paths(workspace)
    violations = [path for path in changed if path not in ALLOWED_CHANGED_FILES]
    check("修改边界受控", not violations, ", ".join(violations))
    return checks, problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    if not (workspace / "app" / "main.py").is_file():
        raise SystemExit(f"不是融资申请工作区：{workspace}")
    checks, problems = validate(workspace)
    result = {
        "workspace": str(workspace),
        "passed": not problems,
        "problems": problems,
        "checks": checks,
        "changed_files": changed_paths(workspace),
        "boundary_violations": [item["detail"] for item in checks if item["name"] == "修改边界受控" and not item["passed"]],
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        for item in checks:
            print(("PASS" if item["passed"] else "BLOCKER"), item["name"], item["detail"])
        print("\nOVERALL:", "PASS" if result["passed"] else "BLOCKER")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
