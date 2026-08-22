"""独立 shared-state concurrency 实验，不扩展正式 Suite executor。"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.runtime import RuntimeStore  # noqa: E402


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, value: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_shared_state_experiment(output_path: Path) -> Dict[str, Any]:
    store = RuntimeStore(output_path.parent / "runtime-state.json")
    store.reset()
    prepared = store.prepare_pending_order()
    shared_order_id = prepared["orders"][0]["id"]
    barrier = threading.Barrier(2)
    records: Dict[str, Dict[str, Any]] = {"A": {"timeline": []}, "B": {"timeline": []}}

    def worker(name: str) -> None:
        record = records[name]

        def event(kind: str, **details: Any) -> None:
            record["timeline"].append({"event": kind, "timestamp": utc_now(), **details})

        event("obtained_shared_order", order_id=shared_order_id)
        before = store.order_facts(shared_order_id)
        record["observed_facts_before"] = before
        event("precondition_checked", status=before["order_status"])
        barrier.wait()
        event("barrier_released")
        outcome, payment = store.pay(shared_order_id)
        record["pay_outcome"] = outcome
        record["payment"] = payment
        event("pay_attempted", outcome=outcome)
        after = store.order_facts(shared_order_id)
        record["observed_facts_after"] = after
        event("facts_observed_after", status=after["order_status"], payment_count=after["payment_count"])

    threads = [threading.Thread(target=worker, args=(name,)) for name in ("A", "B")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    final_facts = store.order_facts(shared_order_id)
    duplicate_outcome = sum(records[name]["pay_outcome"] == "already_paid" for name in records)
    summary = {
        "result": "STATE_CONTAMINATION_OBSERVED" if duplicate_outcome == 1 else "NOT_OBSERVED",
        "shared_order_id": shared_order_id,
        "worker_a": records["A"],
        "worker_b": records["B"],
        "final_business_facts": final_facts,
        "duplicate_business_action_count": duplicate_outcome,
        "observed_at": utc_now(),
    }
    _write_json(output_path, summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts" / "round5" / "shared-state-concurrency" / "summary.json")
    args = parser.parse_args()
    summary = run_shared_state_experiment(args.output.resolve())
    print(json.dumps({key: summary[key] for key in ("result", "duplicate_business_action_count")}, ensure_ascii=False))
    return 0 if summary["result"] == "STATE_CONTAMINATION_OBSERVED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
