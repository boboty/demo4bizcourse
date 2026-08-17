"""演示前一键环境自检：只查环境是否就绪，不跑业务测试逻辑（业务测试见 validate_demo.py）。"""

import importlib.metadata
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MIN_PYTHON = (3, 11)
LOCK_FILE = PROJECT_ROOT / "requirements.lock.txt"


def _expected_versions() -> dict[str, str]:
    expected = {}
    for line in LOCK_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or "==" not in line:
            continue
        name, version = line.split("==", 1)
        expected[name.strip().lower().replace("_", "-")] = version.strip()
    return expected


def check_python_version() -> tuple[bool, str]:
    ok = sys.version_info[:2] >= MIN_PYTHON
    return ok, f"Python {sys.version.split()[0]} (need >= {'.'.join(map(str, MIN_PYTHON))})"


def check_pinned_packages() -> tuple[bool, str]:
    mismatches = []
    for name, expected_version in _expected_versions().items():
        try:
            installed = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            mismatches.append(f"{name}: MISSING (expect {expected_version})")
            continue
        if installed != expected_version:
            mismatches.append(f"{name}: {installed} (expect {expected_version})")
    if mismatches:
        return False, "; ".join(mismatches)
    return True, f"{len(_expected_versions())} packages match requirements.lock.txt"


def check_app_boots() -> tuple[bool, str]:
    sys.path.insert(0, str(PROJECT_ROOT))
    try:
        from fastapi.testclient import TestClient

        from app.main import create_app

        with TestClient(create_app()) as client:
            health = client.get("/health")
            preview = client.post(
                "/api/orders/discount-preview",
                json={"customerLevel": "GOLD", "amount": 1200, "coupon": "VIP100"},
            )
        ok = health.status_code == 200 and preview.status_code == 200 and preview.json()["finalAmount"] == 1000
        return ok, f"health={health.status_code} preview={preview.status_code} finalAmount={preview.json().get('finalAmount')}"
    except Exception as exc:  # noqa: BLE001 - smoke check must report, not raise
        return False, f"app failed to boot: {exc!r}"


def check_no_network_needed() -> tuple[bool, str]:
    wheels_dir = PROJECT_ROOT / "vendor" / "wheels"
    count = len(list(wheels_dir.glob("*.whl"))) if wheels_dir.is_dir() else 0
    ok = count >= len(_expected_versions())
    return ok, f"{count} vendored wheel(s) in vendor/wheels/ (offline reinstall available if venv is rebuilt)"


def main() -> int:
    checks = [
        ("Python version", check_python_version),
        ("Pinned packages", check_pinned_packages),
        ("App boots + answers", check_app_boots),
        ("Offline reinstall available", check_no_network_needed),
    ]
    print("SMOKE CHECK\n")
    all_ok = True
    for label, fn in checks:
        ok, detail = fn()
        all_ok &= ok
        print(f"{label:.<28} {'PASS' if ok else 'FAILED'}  ({detail})")
    print(f"\nSMOKE STATUS: {'READY' if all_ok else 'NOT READY'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
