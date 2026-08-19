"""课前自检：确认 Demo 处于可开课状态。

只读检查，不修复任何代码。逐项输出检查结果；全部通过时最终输出 DEMO READY，
否则输出 DEMO NOT READY 并列出不通过项。
"""

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import create_app  # noqa: E402


BUSINESS_RULES = PROJECT_ROOT / "docs" / "business-rules.md"
WORKSPACE = PROJECT_ROOT / "agent_workspace"
WORKSPACE_ALLOWED = {"README.md", ".gitkeep", ".DS_Store"}

REQUIRED_CASES = (
    {"memberLevel": "GOLD", "amount": 999},
    {"memberLevel": "GOLD", "amount": 1000},
    {"memberLevel": "GOLD", "amount": 1001},
    {"memberLevel": "SILVER", "amount": 1000},
    {"memberLevel": "STANDARD", "amount": 1000},
)


def gold_1000_payload() -> dict:
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/orders/calculate",
            json={"memberLevel": "GOLD", "amount": 1000},
        )
    assert response.status_code == 200, response.text
    return response.json()


def check_app_loads() -> bool:
    with TestClient(create_app()) as client:
        return client.get("/health").status_code == 200


def check_endpoint_declared() -> bool:
    with TestClient(create_app()) as client:
        schema = client.get("/openapi.json")
    if schema.status_code != 200:
        return False
    post = schema.json().get("paths", {}).get("/api/orders/calculate", {}).get("post")
    return post is not None


def check_gold_1000_http_ok() -> bool:
    try:
        return gold_1000_payload().get("status") == "SUCCESS"
    except Exception:
        return False


def check_discount_is_200() -> bool:
    try:
        return gold_1000_payload().get("discount") == 200
    except Exception:
        return False


def check_bug_still_present() -> bool:
    try:
        payload = gold_1000_payload()
        return payload.get("discount") == 200 and payload.get("finalAmount") == 1000
    except Exception:
        return False


def check_business_rules_document() -> bool:
    if not BUSINESS_RULES.is_file():
        return False
    text = BUSINESS_RULES.read_text(encoding="utf-8")
    required_fragments = (
        "finalAmount = amount - discount",
        "GOLD",
        "SILVER",
        "STANDARD",
        "200",
        "100",
        "800",
    )
    return all(fragment in text for fragment in required_fragments)


def check_required_cases_http_ok() -> bool:
    with TestClient(create_app()) as client:
        for case in REQUIRED_CASES:
            response = client.post("/api/orders/calculate", json=case)
            if response.status_code != 200 or response.json().get("status") != "SUCCESS":
                return False
    return True


def check_workspace_clean() -> bool:
    if not WORKSPACE.is_dir():
        return False
    for child in WORKSPACE.iterdir():
        if child.name in WORKSPACE_ALLOWED:
            continue
        return False
    return True


def main() -> int:
    checks = [
        ("服务可正常加载 (/health)", check_app_loads),
        ("订单接口存在 (POST /api/orders/calculate)", check_endpoint_declared),
        ("GOLD + 1000 返回 HTTP 200 + status=SUCCESS", check_gold_1000_http_ok),
        ("GOLD + 1000 discount = 200", check_discount_is_200),
        ("当前故意 Bug 仍存在：finalAmount = 1000", check_bug_still_present),
        ("docs/business-rules.md 规定正确值 800 (amount - discount)", check_business_rules_document),
        ("五组必测用例均 HTTP 200 + status=SUCCESS", check_required_cases_http_ok),
        ("agent_workspace 已清空或已 Reset", check_workspace_clean),
    ]

    print("DEMO PRE-FLIGHT CHECK\n")
    failed: list[str] = []
    for label, fn in checks:
        ok = bool(fn())
        print(f"[{'PASS' if ok else 'FAILED'}] {label}")
        if not ok:
            failed.append(label)

    print()
    if not failed:
        print("DEMO READY")
        return 0
    print("DEMO NOT READY - 以下项目未通过：")
    for label in failed:
        print(f"  - {label}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
