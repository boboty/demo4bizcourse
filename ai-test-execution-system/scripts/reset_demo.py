#!/usr/bin/env python3
"""恢复 Round 0.5 的固定课堂 baseline。"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.runtime import RuntimeStore  # noqa: E402
from self_heal.writeback import restore_baseline_locator  # noqa: E402


def main() -> None:
    restore_baseline_locator(PROJECT_ROOT / "cases" / "pay_order.yaml")
    state = RuntimeStore().reset()
    order = state["orders"][0]
    print("baseline restored: {0} ({1}), inventory=10, payments=0".format(order["id"], order["status"]))


if __name__ == "__main__":
    main()
