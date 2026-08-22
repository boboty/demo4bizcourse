import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_golden_case_input_is_complete():
    cases = json.loads((ROOT / "validation/cases.json").read_text(encoding="utf-8"))
    assert [case["id"] for case in cases] == ["GC-01", "GC-02", "GC-03", "GC-04"]
    assert all("fx_loss_eligible" in case and "tax_refund_eligible" in case for case in cases)


def test_independent_instructions_require_black_box_sequence():
    instructions = (ROOT / "validation/independent-validation.md").read_text(encoding="utf-8")
    assert "形成独立期望结果" in instructions
    assert "bin/actual-output" in instructions
