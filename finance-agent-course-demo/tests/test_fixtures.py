from app.fixtures.finance_data import finance_fixture
from app.fixtures.validation_data import validation_fixture


def test_finance_fixture_matches_course_story() -> None:
    data = finance_fixture()
    assert data["company"]["name"] == "华启制造有限公司"
    assert data["transaction"]["amount"] == "¥58,600.00"
    assert data["transaction"]["payer"] == "华远商贸有限公司"
    assert len(data["unmatched_receivables"]) == 4
    assert any(row["amount"] == "¥58,600" for row in data["unmatched_receivables"])
    assert len(data["historical_payments"]) == 3


def test_batch_fixture_has_fixed_counts_and_representative_rows() -> None:
    data = finance_fixture()
    summary = data["batch_summary"]
    assert summary == {"batch_id": "BW-202607-04", "total": 40, "drafted": 37, "investigating": 3, "posted": 0}
    assert len(data["batch_rows"]) == 10
    assert data["batch_rows"][0]["status"] == "待调查"


def test_permission_fixture_preserves_business_boundaries() -> None:
    permissions = finance_fixture()["permissions"]
    assert "生成凭证草稿" in permissions["allowed"]
    assert "自动过账" in permissions["forbidden"]
    assert "自动核销存在歧义的应收" in permissions["forbidden"]


def test_validation_fixture_keeps_rule_and_wrong_conclusion_separate() -> None:
    data = validation_fixture()
    assert data["rule"]["correct"][0].startswith("先正常评估 A")
    assert data["rule"]["misunderstood"] == ["同时发现 A 和 B 时，直接优先选择 B"]
    assert data["tests"] == [("Implementation", "PASS"), ("Unit Tests", "PASS"), ("Integration Tests", "PASS"), ("Regression Tests", "PASS")]
    assert data["final_status"] == "验收未通过"

