import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.settlement.service import evaluate_candidate
cases = json.loads((ROOT / "validation/cases.json").read_text(encoding="utf-8"))
expected = {x["id"]: x for x in json.loads((ROOT / "instructor/golden/settlement_expected.json").read_text(encoding="utf-8"))}

failed = []
for case in cases:
    actual = {"id": case["id"], **evaluate_candidate(case)}
    exp = expected[case["id"]]
    ok = actual == exp
    print(("PASS" if ok else "BLOCKER"), case["id"], "expected=", exp, "actual=", actual)
    if not ok:
        failed.append(case["id"])

if failed:
    print()
    print("OVERALL: BLOCKER — independent business validation found mismatches:", ", ".join(failed))
    raise SystemExit(1)
print()
print("OVERALL: PASS")
