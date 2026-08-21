import json
from pathlib import Path

import yaml

from self_heal.analyzer import build_request, import_interactive_candidate
from self_heal.candidate import Locator, RepairCandidate
from self_heal.reviewer import review_candidate
from self_heal.writeback import restore_baseline_locator, write_back


ROOT = Path(__file__).resolve().parents[1]
V1 = {"using": "css selector", "value": "#pay-now"}
V2 = {"using": "css selector", "value": "[data-testid='confirm-payment']"}


def candidate() -> RepairCandidate:
    return RepairCandidate(
        target="pay_button",
        old_locator=Locator(**V1),
        candidate=Locator(**V2),
        evidence={"unique_match": True, "semantic_text": "确认支付"},
        provenance={"kind": "openai_responses_api", "model": "test", "response_id": "test", "generated_at": "now"},
    )


def test_reviewer_approves_only_unique_v2_payment_candidate() -> None:
    review = review_candidate(
        ROOT / "cases" / "pay_order.yaml",
        candidate(),
        '<main><button data-testid="confirm-payment">确认支付</button></main>',
    )
    assert review["decision"] == "APPROVED"
    assert review["unique_match_count"] == 1
    assert review["candidate_locator"] == V2


def test_reviewer_rejects_non_unique_candidate_and_preserves_fixed_facts(tmp_path: Path) -> None:
    case = yaml.safe_load((ROOT / "cases" / "pay_order.yaml").read_text(encoding="utf-8"))
    case["assertions"]["api_facts"]["equals"]["inventory.available_quantity"] = 10
    case_path = tmp_path / "case.yaml"
    case_path.write_text(yaml.safe_dump(case, allow_unicode=True), encoding="utf-8")
    review = review_candidate(
        case_path,
        candidate(),
        '<button data-testid="confirm-payment"></button><button data-testid="confirm-payment"></button>',
    )
    assert review["decision"] == "REJECTED"
    assert any("固定 API" in reason for reason in review["reasons"])
    assert any("匹配 2" in reason for reason in review["reasons"])


def test_writeback_is_one_locator_line_and_restore_is_reversible(tmp_path: Path) -> None:
    case_path = tmp_path / "pay_order.yaml"
    before = (ROOT / "cases" / "pay_order.yaml").read_text(encoding="utf-8")
    case_path.write_text(before, encoding="utf-8")
    review = {"decision": "APPROVED"}
    verification = {"runs": [{"result": "PASS"}, {"result": "PASS"}, {"result": "PASS"}]}
    audit = write_back(case_path, candidate(), review, verification, tmp_path / "writeback.json")
    after = case_path.read_text(encoding="utf-8")
    assert audit["before"] == V1
    assert audit["after"] == V2
    assert after.replace("[data-testid='confirm-payment']", "#pay-now") == before
    assert restore_baseline_locator(case_path) is True
    assert case_path.read_text(encoding="utf-8") == before


def test_analyzer_request_contains_real_image_input_and_structured_candidate_contract(tmp_path: Path) -> None:
    screenshot = tmp_path / "failure.png"
    screenshot.write_bytes(b"not-a-real-png-but-real-file-input-for-request-shape")
    request = build_request(
        {"failure_step": "pay_order", "old_locator": V1, "target_semantic": "支付当前待付款订单"},
        '<button data-testid="confirm-payment">确认支付</button>',
        screenshot,
        "gpt-4o",
    )
    assert request["store"] is False
    content = request["input"][0]["content"]
    assert content[1]["type"] == "input_image"
    assert content[1]["image_url"].startswith("data:image/png;base64,")
    schema = request["text"]["format"]["schema"]
    assert set(schema["properties"]) == {"target", "old_locator", "candidate", "evidence"}


def test_interactive_import_is_explicitly_labeled_and_bound_to_real_old_locator(tmp_path: Path) -> None:
    failure = tmp_path / "failure.json"
    failure.write_text('{"failure_step":"pay_order","old_locator":{"using":"css selector","value":"#pay-now"},"target_semantic":"支付当前待付款订单"}', encoding="utf-8")
    raw = tmp_path / "raw.json"
    raw.write_text(json.dumps({
        "target": "pay_button", "old_locator": V1, "candidate": V2,
        "evidence": {"unique_match": True, "semantic_text": "确认支付"},
    }, ensure_ascii=False), encoding="utf-8")
    imported = import_interactive_candidate(raw, failure, tmp_path / "imported.json")
    assert imported.provenance["kind"] == "interactive_codex_export"
    assert imported.candidate.value == "[data-testid='confirm-payment']"
