from pathlib import Path

from scripts.run_pay_order_ios import read_case
from skills.assert_business_state import REQUIRED_FACTS, assert_business_state
from skills.contracts import ExecutionContext, SkillError
from skills.prepare_pending_order import prepare_pending_order


ROOT = Path(__file__).resolve().parents[1]


def test_task_schema_freezes_round3_workflow_and_required_facts() -> None:
    case = read_case(ROOT / "cases" / "pay_order.yaml")
    assert case["version"] == 1
    assert case["workflow"]["name"] == "pay_order_and_verify"
    assert case["workflow"]["steps"] == [
        "prepare_pending_order",
        "login",
        "open_pending_order",
        "pay_order",
        "assert_business_state",
        "reset_test_state",
    ]
    assert case["assertions"]["api_facts"]["equals"] == REQUIRED_FACTS


def test_prepare_skill_verifies_initial_order_payment_and_inventory(monkeypatch, tmp_path: Path) -> None:
    import skills.prepare_pending_order as module

    responses = [
        {"user_id": "user-course-demo", "order_id": "order-001", "order_status": "PENDING_PAY"},
        {
            "order_id": "order-001",
            "order_status": "PENDING_PAY",
            "payment_count": 0,
            "inventory": {"available_quantity": 10},
        },
    ]
    monkeypatch.setattr(module, "require_success", lambda *args, **kwargs: responses.pop(0))
    case = read_case(ROOT / "cases" / "pay_order.yaml")
    context = ExecutionContext("http://demo", case, object(), tmp_path)
    result = prepare_pending_order(context)
    assert result["order_id"] == "order-001"
    assert context.user == {"id": "user-course-demo"}


def test_business_state_skill_is_independent_and_rejects_changed_fixed_facts(monkeypatch, tmp_path: Path) -> None:
    import skills.assert_business_state as module

    case = read_case(ROOT / "cases" / "pay_order.yaml")
    context = ExecutionContext("http://demo", case, object(), tmp_path, order_id="order-001")
    monkeypatch.setattr(module, "require_success", lambda *args, **kwargs: {
        "order_status": "PAID",
        "payment_count": 1,
        "payment_record": {"status": "SUCCEEDED"},
        "inventory": {"available_quantity": 9},
    })
    assert assert_business_state(context)["api_result"] == "PASS"

    case["assertions"]["api_facts"]["equals"]["payment_count"] = 2
    try:
        assert_business_state(context)
    except SkillError as error:
        assert error.code == "BUSINESS_STATE_ASSERTION_FAILED"
    else:
        raise AssertionError("修改固定 API facts 后必须失败")
