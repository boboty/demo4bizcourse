#!/usr/bin/env python3
"""恢复 Round 2 课堂起点：V1 旧 locator、默认业务配置与清洁运行产物。"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.runtime import RuntimeStore  # noqa: E402
from self_heal.writeback import restore_baseline_locator  # noqa: E402


def main() -> int:
    changed = restore_baseline_locator(PROJECT_ROOT / "cases" / "pay_order.yaml")
    RuntimeStore().reset()
    candidate_dir = PROJECT_ROOT / "self_heal" / "candidates"
    for path in candidate_dir.glob("*.json"):
        path.unlink()
    print("Round 2 baseline restored: locator=#pay-now, ui=v1, payment=normal, product_bug=off, locator_changed={0}".format(changed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
