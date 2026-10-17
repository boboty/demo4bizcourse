import copy

import pytest
from fastapi.testclient import TestClient

from app.demo_a import CONFIDENTIAL_ID, CONTRACT_TEXT
from app.demo_a import state as a_state
from app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        test_client.post("/api/v1/a/reset")
        test_client.post("/api/v1/reset")
        yield test_client


def identify(client, document_id="PO-A-017", **extra):
    return client.post(f"/api/v1/a/documents/{document_id}/identify", json=extra)


def process(client, run, **extra):
    if run["document_id"] == "PO-A-017" and not extra:
        client.post(f"/api/v1/a/runs/{run['id']}/assistant-review", json={})
        client.post(f"/api/v1/a/runs/{run['id']}/correction", json={
            "evidence": "128000 元", "suggested_category": "personal",
            "corrected_category": "ordinary", "reason": "金额不是可识别自然人的证据。",
        })
        client.post(f"/api/v1/a/runs/{run['id']}/preview", json={})
        extra = {"confirmation": "CONFIRM_NEXT_STEP"}
    return client.post(
        f"/api/v1/a/documents/{run['document_id']}/process/{run['id']}",
        json=extra,
    )


def test_deterministic_identification_and_authorized_server_redaction(client):
    identified = identify(client).json()
    assert identified["source_text"] == CONTRACT_TEXT
    assert {field["category"] for field in identified["fields"]} == {"ordinary", "personal", "commercial"}
    assert all(field["evidence"] == field["value"] for field in identified["fields"])
    personal = {field["label"]: field for field in identified["fields"] if field["category"] == "personal"}
    assert personal["身份证号"]["value"] == "110101199001010016"
    assert len(personal["身份证号"]["value"]) == 18
    assert personal["联系电话"]["value"] == "19900000000"
    assert len(personal["联系电话"]["value"]) == 11
    assert personal["身份证号"]["start"] == CONTRACT_TEXT.index("110101199001010016")
    assert personal["身份证号"]["evidence"] == "110101199001010016"
    assert personal["联系电话"]["start"] == CONTRACT_TEXT.index("19900000000")
    assert personal["联系电话"]["evidence"] == "19900000000"
    assert "身份证号" in personal["身份证号"]["rule"] and "联系电话" in personal["联系电话"]["rule"]
    result = process(client, identified)
    assert result.status_code == 200
    body = result.json()
    assert body["authorization"] == "ALLOW"
    assert "HT-DEMO-017" in body["after"] and "128000 元" in body["after"]
    assert "110101199001010016" not in body["after"] and "19900000000" not in body["after"]
    assert "3200 元/台" not in body["after"]
    assert body["after"].count("[已脱敏]") == 6
    assert "不保证匿名化" in body["notice"]
    assert [audit["action"] for audit in client.get("/api/v1/a/state").json()["audits"]] == [
        "identify", "assistant_identify", "human_correction", "redaction_preview", "deidentify"
    ]


def test_identified_unapproved_document_is_denied_before_redaction(monkeypatch, client):
    import app.demo_a as module

    identified = identify(client, "PO-A-018").json()
    before = copy.deepcopy(a_state["counters"])

    def should_not_run(*_args):
        raise AssertionError("未授权资料不得进入脱敏函数")

    monkeypatch.setattr(module, "redact_fields", should_not_run)
    denied = process(client, identified)
    assert denied.status_code == 403
    assert denied.json()["authorization"] == "DENY"
    assert a_state["counters"] == before
    assert client.get("/api/v1/a/state").json()["audits"][-1]["authorization"] == "DENY"


@pytest.mark.parametrize(
    ("action", "body"),
    [
        ("identify", {}),
        ("process/forged-run", {}),
        ("upload", {}),
    ],
)
def test_confidential_boundary_precedes_all_processing_paths(client, action, body):
    before = copy.deepcopy(a_state["counters"])
    route = action if action != "process" else "process/boundary-probe"
    response = client.post(f"/api/v1/a/documents/{CONFIDENTIAL_ID}/{route}", json=body)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CONFIDENTIAL_BOUNDARY"
    assert a_state["counters"] == before
    assert len(a_state["runs"]) == 0
    audit = client.get("/api/v1/a/state").json()["audits"][-1]
    assert audit["authorization"] == "DENY" and audit["document_id"] == CONFIDENTIAL_ID
    assert "TOP-SECRET-DEMO-CONTENT" not in str(audit)


@pytest.mark.parametrize("path", [
    "/api/v1/a/documents/PO-A-017/identify",
    "/api/v1/a/documents/PO-A-017/upload",
])
def test_client_cannot_supply_privilege_category_or_document_body(client, path):
    response = client.post(path, json={"role": "admin", "category": "ordinary", "approved": True,
                                       "text": "任意涉密正文"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_INPUT"
    assert client.get("/api/v1/a/state").json()["audits"] == []


def test_confidential_body_is_rejected_before_read_or_processing(monkeypatch, client, capsys):
    import app.demo_a as module

    def should_not_run():
        raise AssertionError("涉密正文不得进入识别逻辑")

    monkeypatch.setattr(module, "identify_fields", should_not_run)
    monkeypatch.setattr(module, "redact_fields", should_not_run)
    sensitive_body = b'{"text":"TOP-SECRET-DEMO-CONTENT", "role":"admin", "category":"ordinary"}'
    for path in [
        f"/api/v1/a/documents/{CONFIDENTIAL_ID}/identify",
        f"/api/v1/a/documents/{CONFIDENTIAL_ID}/process/boundary-probe",
        f"/api/v1/a/documents/{CONFIDENTIAL_ID}/upload",
    ]:
        response = client.post(path, content=sensitive_body, headers={"Content-Type": "application/json"})
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "CONFIDENTIAL_BOUNDARY"
    captured = capsys.readouterr()
    assert "TOP-SECRET-DEMO-CONTENT" not in captured.out + captured.err


def test_client_cannot_change_process_identity_or_fields(client):
    run = identify(client).json()
    response = process(client, run, role="admin", category="ordinary", fields=[])
    assert response.status_code == 422
    assert client.get("/api/v1/a/state").json()["audits"] == [run["audit"]]


def test_a_human_review_and_explicit_confirmation_are_required(client):
    run = identify(client).json()
    path = f"/api/v1/a/documents/{run['document_id']}/process/{run['id']}"
    assert client.post(path, json={"confirmation": "CONFIRM_NEXT_STEP"}).status_code == 409
    assert client.post(f"/api/v1/a/runs/{run['id']}/assistant-review", json={}).status_code == 200
    correction = {"evidence": "128000 元", "suggested_category": "personal",
                  "corrected_category": "ordinary", "reason": "金额不是可识别自然人的证据。"}
    assert client.post(f"/api/v1/a/runs/{run['id']}/correction",
                       json={**correction, "evidence": "恒川设备"}).status_code == 422
    assert client.post(f"/api/v1/a/runs/{run['id']}/correction", json=correction).status_code == 200
    assert client.post(path, json={"confirmation": "CONFIRM_NEXT_STEP"}).status_code == 409
    assert client.post(f"/api/v1/a/runs/{run['id']}/preview", json={}).status_code == 200
    assert client.post(path, json={}).status_code == 422
    assert client.post(path, json={"confirmation": "CONFIRM_NEXT_STEP"}).status_code == 200



def test_a_reset_invalidates_only_a_state_and_b_reset_stays_independent(client):
    run = identify(client).json()
    process(client, run)
    b_run = client.post("/api/v1/runs", json={"polluted": True}).json()
    reset = client.post("/api/v1/a/reset").json()
    assert reset["runs"] == {} and reset["audits"] == []
    assert reset["counters"] == {"identification": 0, "deidentification": 0, "upload": 0}
    assert process(client, run).status_code == 404
    assert b_run["id"] in client.get("/api/v1/state").json()["runs"]
    assert client.post("/api/v1/a/documents/PO-A-018/identify", json={}).status_code == 201
    client.post("/api/v1/reset")
    assert client.get("/api/v1/a/state").json()["runs"]


def test_a_page_and_assets_are_offline_and_separate(client):
    assert client.get("/demo/a").status_code == 200
    assert client.get("/demo/b").status_code == 200
    assert "演示涉密前置阻断" in client.get("/demo/a").text
    assert "DOC-CLASSIFIED-009" in client.get("/static/demo-a.js").text
    assert client.get("/api/v1/a/documents").json()["items"][-1]["body_available"] is False
    for path in ["demo-a.js", "demo-a.css", "design-system/styles.css", "design-system/tokens/fonts.css"]:
        assert client.get(f"/static/{path}").status_code == 200
    assert "@import" not in client.get("/static/design-system/tokens/fonts.css").text
