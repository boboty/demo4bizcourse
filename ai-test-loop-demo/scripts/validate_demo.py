"""对课堂故事和本地可重复性进行统一验收。"""

import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import create_app  # noqa: E402


REQUIRED_ASSETS = (
    "business/requirement.md",
    "business/acceptance.md",
    "business/api-rules.md",
    "api/openapi.yaml",
    "tasks/task-package.md",
    "skills/api-test-skill.md",
    "docs/classroom-script.md",
)


def run_script(name: str, *args: str) -> tuple[bool, str]:
    result = subprocess.run(
        [sys.executable, f"scripts/{name}", *args],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.returncode == 0, result.stdout + result.stderr


def application_and_openapi_are_consistent() -> bool:
    with TestClient(create_app()) as client:
        health = client.get("/health")
        schema = client.get("/openapi.json")
        preview = client.post(
            "/api/orders/discount-preview",
            json={"customerLevel": "GOLD", "amount": 1200, "coupon": "VIP100"},
        )
    if health.json() != {"status": "ok"} or schema.status_code != 200 or preview.status_code != 200:
        return False
    generated_schema = schema.json()
    route = generated_schema.get("paths", {}).get("/api/orders/discount-preview", {}).get("post")
    response_properties = generated_schema.get("components", {}).get("schemas", {}).get(
        "DiscountPreviewResponse", {}
    ).get("properties", {})
    declared = (PROJECT_ROOT / "api" / "openapi.yaml").read_text(encoding="utf-8")
    expected_fields = ("membershipDiscount", "couponDiscount", "discountSources", "decisionTrace")
    return bool(route) and all(field in response_properties and field in declared for field in expected_fields)


def has_no_online_dependency() -> bool:
    requirements = (PROJECT_ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    code = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (PROJECT_ROOT / "app").glob("*.py")
    ).lower()
    return not any(marker in requirements or marker in code for marker in ("openai", "requests", "urllib"))


def main() -> int:
    checks: list[tuple[str, bool]] = []
    reset_first, _ = run_script("reset_demo.py")
    reset_second, _ = run_script("reset_demo.py")
    checks.append(("Reset (idempotent)", reset_first and reset_second))
    checks.append(("Application", application_and_openapi_are_consistent()))
    checks.append(("OpenAPI / implementation", application_and_openapi_are_consistent()))
    checks.append(("Required assets", all((PROJECT_ROOT / asset).is_file() for asset in REQUIRED_ASSETS)))
    checks.append(("No online dependency", has_no_online_dependency()))

    generated_ok, generated_output = run_script("run_generated_tests.py")
    checks.append(("Generated tests", generated_ok and "ALL TESTS PASSED" in generated_output))
    generated_review_ok, generated_review_output = run_script("run_independent_review.py")
    checks.append(("Independent review", generated_review_ok and "INDEPENDENT REVIEW : REJECTED" in generated_review_output))

    verified_ok, verified_output = run_script("run_verified_tests.py")
    checks.append(("Verified tests", verified_ok and "ALL VERIFIED TESTS PASSED" in verified_output))
    final_review_ok, final_review_output = run_script("run_independent_review.py", "--target", "verified")
    checks.append(("Final independent review", final_review_ok and "INDEPENDENT REVIEW : PASS" in final_review_output))

    evidence_files = (
        PROJECT_ROOT / "evidence" / "generated-test-report.md",
        PROJECT_ROOT / "evidence" / "independent-review-report.md",
        PROJECT_ROOT / "evidence" / "final-test-report.md",
    )
    evidence_ok = all(path.is_file() for path in evidence_files)
    if evidence_ok:
        evidence_ok = (
            "pytest: PASS" in evidence_files[0].read_text(encoding="utf-8")
            and "RESULT: REJECTED" in evidence_files[1].read_text(encoding="utf-8")
            and "RESULT: PASS" in evidence_files[2].read_text(encoding="utf-8")
        )
    checks.append(("Evidence", evidence_ok))

    print("AI TEST LOOP DEMO VALIDATION\n")
    for name, passed in checks:
        suffix = "PASS" if passed else "FAILED"
        if name == "Independent review" and passed:
            suffix = "REJECTED (EXPECTED)"
        print(f"{name:.<28} {suffix}")
    ready = all(passed for _, passed in checks)
    print(f"\nDEMO STATUS: {'READY' if ready else 'NOT READY'}")
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
