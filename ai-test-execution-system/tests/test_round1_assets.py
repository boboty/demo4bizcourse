from pathlib import Path

from scripts.run_pay_order_ios import assert_equals, read_case


ROOT = Path(__file__).resolve().parents[1]


def test_final_round1_case_is_physical_ios_v1_and_uses_dynamic_order_id() -> None:
    case = read_case(ROOT / "cases" / "pay_order.yaml")
    assert case["device"]["physical"] is True
    assert case["device"]["platform"] == "iOS"
    assert case["configuration"]["ui_version"] == "v1"
    assert case["test_data"]["order_id_response_field"] == "order_id"
    assert "{order_id}" in case["assertions"]["api_facts"]["endpoint"]
    assert case["ui"]["steps"][-1]["locator"]["value"] == "#pay-now"


def test_final_round1_case_requires_business_facts_not_only_ui_text() -> None:
    case = read_case(ROOT / "cases" / "pay_order.yaml")
    expected = case["assertions"]["api_facts"]["equals"]
    assert expected == {
        "order_status": "PAID",
        "payment_count": 1,
        "payment_record.status": "SUCCEEDED",
        "inventory.available_quantity": 9,
    }
    assert_equals(
        {
            "order_status": "PAID",
            "payment_count": 1,
            "payment_record": {"status": "SUCCEEDED"},
            "inventory": {"available_quantity": 9},
        },
        expected,
        "测试",
    )
