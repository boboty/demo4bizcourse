from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.runtime import RuntimeStore


def make_client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(RuntimeStore(tmp_path / "state.json")))


def configure(client: TestClient, **settings: str) -> None:
    response = client.put("/api/config", json=settings)
    assert response.status_code == 200


def test_prepare_pending_order_and_normal_payment_updates_independent_facts(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    prepared = client.post("/api/test-data/prepare-pending-order")
    assert prepared.status_code == 200
    assert prepared.json()["order_status"] == "PENDING_PAY"
    order_id = prepared.json()["order_id"]

    paid = client.post("/api/orders/{0}/pay".format(order_id))
    assert paid.status_code == 200
    facts = client.get("/api/orders/{0}/facts".format(order_id)).json()
    assert facts["order_status"] == "PAID"
    assert facts["payment_count"] == 1
    assert facts["payment_record"]["status"] == "SUCCEEDED"
    assert facts["inventory"]["available_quantity"] == 9


def test_timeout_before_commit_keeps_all_business_facts_unchanged(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    configure(client, payment_mode="timeout_before_commit")
    response = client.post("/api/orders/order-001/pay")
    assert response.status_code == 504
    facts = client.get("/api/orders/order-001/facts").json()
    assert facts["order_status"] == "PENDING_PAY"
    assert facts["payment_count"] == 0
    assert facts["inventory"]["available_quantity"] == 10


def test_timeout_after_commit_reports_failure_but_keeps_committed_business_facts(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    configure(client, payment_mode="timeout_after_commit")
    response = client.post("/api/orders/order-001/pay")
    assert response.status_code == 504
    facts = client.get("/api/orders/order-001/facts").json()
    assert facts["order_status"] == "PAID"
    assert facts["payment_count"] == 1
    assert facts["inventory"]["available_quantity"] == 9


def test_product_bug_keeps_inventory_unchanged_after_successful_payment(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    configure(client, product_bug_mode="on")
    assert client.post("/api/orders/order-001/pay").status_code == 200
    facts = client.get("/api/orders/order-001/facts").json()
    assert facts["order_status"] == "PAID"
    assert facts["payment_count"] == 1
    assert facts["inventory"]["available_quantity"] == 10


def test_ui_v1_and_v2_have_exclusive_payment_locators(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    v1 = client.get("/").text
    assert 'id="pay-now"' in v1
    assert 'data-testid="confirm-payment"' not in v1

    configure(client, ui_version="v2")
    v2 = client.get("/").text
    assert 'id="pay-now"' not in v2
    assert 'data-testid="confirm-payment"' in v2


def test_reset_is_repeatable_and_restores_baseline(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    configure(client, ui_version="v2", payment_mode="timeout_after_commit", product_bug_mode="on")
    assert client.post("/api/orders/order-001/pay").status_code == 504

    first = client.post("/api/reset").json()
    second = client.post("/api/reset").json()
    assert first == second
    assert first["settings"] == {"ui_version": "v1", "payment_mode": "normal", "product_bug_mode": "off"}
    facts = client.get("/api/orders/order-001/facts").json()
    assert facts["order_status"] == "PENDING_PAY"
    assert facts["payment_count"] == 0
    assert facts["inventory"]["available_quantity"] == 10
