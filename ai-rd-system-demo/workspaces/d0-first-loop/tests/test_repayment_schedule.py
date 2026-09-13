import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.repayment.service import build_schedule

client = TestClient(app)


def test_schedule_has_one_installment_per_period():
    schedule = build_schedule(total_amount=1000.0, periods=4)
    assert [row["period"] for row in schedule] == [1, 2, 3, 4]


def test_schedule_amounts_keep_two_decimals():
    schedule = build_schedule(total_amount=999.99, periods=7)
    assert all(row["amount"] == round(row["amount"], 2) for row in schedule)


def test_schedule_total_equals_loan_amount():
    schedule = build_schedule(total_amount=100000.0, periods=3)
    amounts = [row["amount"] for row in schedule]
    assert all(amount > 0 for amount in amounts)
    assert round(sum(amounts), 2) == 100000.0


@pytest.mark.parametrize("periods", [0, -3])
def test_schedule_rejects_invalid_periods(periods):
    with pytest.raises(ValueError):
        build_schedule(total_amount=1000.0, periods=periods)


def test_schedule_endpoint_returns_installments():
    response = client.get("/api/repayment-schedule", params={"total_amount": 100000, "periods": 3})
    assert response.status_code == 200
    body = response.json()
    assert body["periods"] == 3
    assert len(body["installments"]) == 3
    assert round(sum(row["amount"] for row in body["installments"]), 2) == 100000.0
