import copy
import json

import pytest
from fastapi.testclient import TestClient

from app.main import ACTOR, CLEAN, INITIAL, app, authorize, model_proposal


@pytest.fixture()
def client():
    with TestClient(app) as c:
        c.post("/api/v1/reset")
        yield c


def proposal(client, polluted=False):
    response = client.post("/api/v1/runs", json={"polluted": polluted})
    assert response.status_code == 201
    return response.json()


def execute(client, run, mode="safe", **overrides):
    body = {"mode": mode, **run["proposal"], **overrides}
    return client.post(f"/api/v1/runs/{run['id']}/executions", json=body)


def test_normal_read_is_real_authorized_query(client):
    run = proposal(client)
    assert run["document"]["text"] == CLEAN
    assert run["proposal"]["action"] == "purchase.read"
    before = client.get("/api/v1/state").json()["stores"]
    response = execute(client, run)
    assert response.status_code == 200
    assert response.json()["authorization"] == "ALLOW"
    assert response.json()["after"] == INITIAL
    assert client.get("/api/v1/state").json()["stores"] == before


def test_same_pollution_proposal_bypass_then_deny_and_replay(client):
    run = proposal(client, True)
    assert model_proposal(run["document"]["text"]) == run["proposal"]
    assert run["proposal"]["action"] == "purchase.approve"
    assert model_proposal(CLEAN)["action"] == "purchase.read"
    before = copy.deepcopy(client.get("/api/v1/state").json()["stores"]["safe"])
    for _ in range(2):
        unsafe = execute(client, run, "unsafe")
        assert unsafe.status_code == 200
        assert unsafe.json()["authorization"] == "BYPASS"
        assert unsafe.json()["after"]["status"] == "已批准"
        safe = execute(client, run)
        assert safe.status_code == 403
        assert safe.json()["authorization"] == "DENY"
        assert safe.json()["before"] == safe.json()["after"] == before
    state = client.get("/api/v1/state").json()
    assert state["stores"]["unsafe"]["status"] == "已批准"
    assert state["stores"]["safe"] == before
    assert len(state["audits"]) == 4
    for audit in state["audits"]:
        assert audit["role"] == ACTOR["role"]
        assert audit["actor_id"] == ACTOR["id"]
        assert audit["run_id"] == run["id"]
        assert audit["request_id"]
        assert audit["object_id"] == INITIAL["id"]
        assert audit["action"] == "purchase.approve"
        assert audit["policy_allowed"] is False


@pytest.mark.parametrize("mode", ["safe", "unsafe"])
@pytest.mark.parametrize(
    "overrides",
    [
        {"action": "purchase.delete"},
        {"object_id": "PO-2026-999"},
        {"arguments": {"status": "已批准", "payment_account": "OTHER"}},
        {"action": "purchase.read", "arguments": {}},
    ],
)
def test_tampering_cannot_escape_proposal_or_object_scope(client, mode, overrides):
    run = proposal(client, True)
    before = client.get("/api/v1/state").json()["stores"]
    response = execute(client, run, mode, **overrides)
    assert response.status_code == 403
    assert response.json()["authorization"] == "DENY"
    assert client.get("/api/v1/state").json()["stores"] == before


@pytest.mark.parametrize("extra", [{"role": "admin"}, {"actor": {"role": "admin"}}, {"approved": True}])
def test_client_cannot_choose_identity(client, extra):
    run = proposal(client, True)
    before = client.get("/api/v1/state").json()["stores"]
    response = execute(client, run, **extra)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_INPUT"
    assert client.get("/api/v1/state").json()["stores"] == before
    assert client.post("/api/v1/runs", json={"polluted": True, **extra}).status_code == 422


def test_policy_is_default_deny():
    assert authorize("procurement_reader", "purchase.read", INITIAL["id"])
    assert not authorize("admin", "purchase.read", INITIAL["id"])
    assert not authorize("procurement_reader", "purchase.read", "OTHER")
    assert not authorize("procurement_reader", "purchase.approve", INITIAL["id"])
    assert not authorize("procurement_reader", "unknown", INITIAL["id"])


def test_reset_invalidates_runs_and_complete_repeat(client):
    old_run = proposal(client, True)
    execute(client, old_run, "unsafe")
    reset = client.post("/api/v1/reset").json()
    assert reset["runs"] == {} and reset["audits"] == []
    assert reset["stores"] == {"safe": INITIAL, "unsafe": INITIAL}
    assert execute(client, old_run, "unsafe").status_code == 404
    new = proposal(client, True)
    assert new["id"] != old_run["id"]
    assert execute(client, new, "unsafe").json()["after"]["status"] == "已批准"
    assert execute(client, new).json()["after"]["status"] == "待审批"


def test_request_ids_and_health(client):
    response = client.get("/api/v1/health", headers={"X-Request-ID": "classroom-123"})
    assert response.headers["X-Request-ID"] == "classroom-123"
    assert response.json()["external_services"] is False
    run = proposal(client)
    response = execute(client, run, role="admin")
    assert response.json()["error"]["request_id"] == response.headers["X-Request-ID"]
    invalid = client.get("/api/v1/state", headers={"X-Request-ID": "bad id"})
    assert invalid.headers["X-Request-ID"] != "bad id"
    assert json.loads(client.get("/api/v1/state").text)["actor"] == ACTOR


def test_local_ui_assets(client):
    assert client.get("/").status_code == 200
    assert client.get("/demo/b").status_code == 200
    for path in ["app.js", "app.css", "design-system/styles.css", "design-system/tokens/fonts.css"]:
        assert client.get("/static/" + path).status_code == 200
    assert "@import" not in client.get("/static/design-system/tokens/fonts.css").text
