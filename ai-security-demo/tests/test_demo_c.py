import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        test_client.post("/api/v1/c/reset")
        test_client.post("/api/v1/a/reset")
        test_client.post("/api/v1/reset")
        yield test_client


def start(client, case_id="C-CASE-101"):
    return client.post("/api/v1/c/runs", json={"case_id": case_id})


def full_evidence(run):
    return [item["id"] for item in run["case"]["evidence"]]


def to_evidence_stage(client, case_id="C-CASE-101"):
    run = start(client, case_id).json()
    analysis = client.post(f"/api/v1/c/runs/{run['id']}/analyze", json={})
    explanation = client.post(f"/api/v1/c/runs/{run['id']}/explain", json={})
    return run, analysis, explanation


def test_case_corpus_has_stable_source_ids_and_all_required_distinct_examples(client):
    response = client.get("/api/v1/c/cases")
    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["id"] for item in items] == ["C-CASE-101", "C-CASE-102", "C-CASE-103"]
    assert all(item["log"]["id"].startswith("LOG-C-") for item in items)
    assert all(item["policy"]["id"].startswith("POL-AI-") for item in items)
    assert all(item["evidence"] for item in items)
    assert items[1]["log"]["tool"] == "browser-shell"
    assert items[1]["log"]["masking"]["mode"] == "未执行"
    assert items[2]["log"]["retention_days"] is None
    whitelist = next(item for item in items[1]["evidence"] if item["id"] == "EVC-C-WHITELIST-01")
    assert whitelist["title"] == "AI 工具准入白名单 · LIST-AI-TOOL-01 v1.0"
    assert "customer-summary" in whitelist["text"] and "research-search" in whitelist["text"]
    assert "未列入本清单的工具不得用于集团业务数据" in whitelist["text"]


def test_rule_engine_uses_call_metadata_and_candidate_questions_link_sources(client):
    run = start(client, "C-CASE-102").json()
    response = client.post(f"/api/v1/c/runs/{run['id']}/analyze", json={})
    assert response.status_code == 200
    analysis = response.json()
    ids = {hit["rule_id"] for hit in analysis["hits"]}
    assert {"RULE-C-TOOL-ALLOWLIST", "RULE-C-SENSITIVE-INPUT", "RULE-C-MASKING-METADATA",
            "RULE-C-ACCESS-METHOD", "RULE-C-EXT-SENSITIVE", "RULE-C-APPROVAL", "RULE-C-RETENTION"} <= ids
    allowlist_hit = next(hit for hit in analysis["hits"] if hit["rule_id"] == "RULE-C-TOOL-ALLOWLIST")
    assert allowlist_hit["evidence"]["whitelist_id"] == "LIST-AI-TOOL-01"
    assert "EVC-C-WHITELIST-01" in allowlist_hit["source_evidence_ids"]
    questions = client.get(f"/api/v1/c/runs/{run['id']}/candidate-questions").json()
    assert questions["items"]
    assert all(item["status"] == "待核实" and item["event_id"] == "LOG-C-102" for item in questions["items"])
    assert all("POL-AI-02" == item["policy_id"] and full_evidence(run) == item["evidence_links"] for item in questions["items"])
    allowlist_question = next(item for item in questions["items"] if item["question_id"] == "Q-RULE-C-TOOL-ALLOWLIST")
    assert "EVC-C-WHITELIST-01" in allowlist_question["evidence_links"]


def test_state_machine_requires_order_and_assistant_cannot_make_final_decision(client):
    run = start(client).json()
    run_id = run["id"]
    assert client.post(f"/api/v1/c/runs/{run_id}/explain", json={}).status_code == 409
    assert client.post(f"/api/v1/c/runs/{run_id}/evidence-check", json={"evidence_ids": ["EVC-C-101-LOG"]}).status_code == 409
    assert client.post(f"/api/v1/c/runs/{run_id}/review", json={"decision": "不违规", "rationale": "事实", "evidence_ids": ["EVC-C-101-LOG"]}).status_code == 409
    assert client.post(f"/api/v1/c/runs/{run_id}/analyze", json={}).status_code == 200
    explanation = client.post(f"/api/v1/c/runs/{run_id}/explain", json={}).json()
    assert explanation["final_decision"] is None
    assert explanation["event_id"] == "LOG-C-101"
    assert explanation["policy_clause"]["id"] == "POL-AI-01"
    assert explanation["evidence_links"] == full_evidence(run)
    assert explanation["pending_verification"]
    assert client.post(f"/api/v1/c/runs/{run_id}/analyze", json={}).status_code == 409


def test_evidence_and_human_decision_are_server_enforced_with_auditable_identity(client):
    run, _, _ = to_evidence_stage(client)
    run_id = run["id"]
    ids = full_evidence(run)
    assert client.post(f"/api/v1/c/runs/{run_id}/evidence-check", json={"evidence_ids": ["FORGED"]}).status_code == 422
    assert client.post(f"/api/v1/c/runs/{run_id}/evidence-check", json={"evidence_ids": [ids[0], ids[0]]}).status_code == 422
    checked = client.post(f"/api/v1/c/runs/{run_id}/evidence-check", json={"evidence_ids": ids})
    assert checked.status_code == 200 and checked.json()["complete"] is True
    assert client.post(f"/api/v1/c/runs/{run_id}/review", json={"decision": "不违规", "rationale": " ", "evidence_ids": ids}).status_code == 422
    forged_role = client.post(f"/api/v1/c/runs/{run_id}/review", json={"decision": "不违规", "rationale": "制度符合", "evidence_ids": ids, "role": "admin"})
    assert forged_role.status_code == 422
    assert client.post(f"/api/v1/c/runs/{run_id}/review", json={"decision": "不违规", "rationale": "未核查证据", "evidence_ids": [ids[0]]}).status_code == 422
    response = client.post(f"/api/v1/c/runs/{run_id}/review", json={"decision": "不违规", "rationale": "原始日志、审批和 POL-AI-01 均能相互印证。", "evidence_ids": ids}, headers={"X-Request-ID": "review-c-101"})
    assert response.status_code == 200
    review = response.json()
    assert review["reviewer"] == {"id": "audit-024", "role": "ai_compliance_reviewer", "name": "合规审计员（固定演示身份）"}
    assert review["decision"] == "不违规" and review["request_id"] == "review-c-101"
    audits = client.get("/api/v1/c/state").json()["audits"]
    assert [item["action"] for item in audits][-4:] == ["deterministic_rule_analysis", "offline_assistant_explanation", "verify_original_evidence", "human_review"]
    assert all(item["actor_id"] == "audit-024" and item["role"] == "ai_compliance_reviewer" and item["run_id"] == run_id for item in audits)
    assert all(item["object_id"] and item["request_id"] for item in audits)
    assert audits[-1]["request_id"] == "review-c-101"
    run_state = client.get("/api/v1/c/state").json()["runs"][run_id]
    run_audits = [item for item in audits if item["run_id"] == run_id]
    assert len(run_state["audit_ids"]) == 5
    assert len(run_state["audit_ids"]) == len(set(run_state["audit_ids"]))
    assert set(run_state["audit_ids"]) == {item["id"] for item in run_audits}


def test_incomplete_case_can_only_be_marked_insufficient_and_explanation_is_careful(client):
    run, analysis, explanation = to_evidence_stage(client, "C-CASE-103")
    assert analysis.json()["status"] == "evidence_needed"
    card = explanation.json()
    assert "尚不能据此确认违规" in card["uncertainty"]
    assert len(card["pending_verification"]) >= 1
    ids = full_evidence(run)
    assert client.post(f"/api/v1/c/runs/{run['id']}/evidence-check", json={"evidence_ids": ids}).status_code == 200
    for decision in ("违规", "不违规"):
        blocked = client.post(f"/api/v1/c/runs/{run['id']}/review", json={"decision": decision, "rationale": "线索看起来异常。", "evidence_ids": ids})
        assert blocked.status_code == 409 and blocked.json()["error"]["code"] == "EVIDENCE_INCOMPLETE"
    allowed = client.post(f"/api/v1/c/runs/{run['id']}/review", json={"decision": "证据不足", "rationale": "资料细分类别、用途与保留期限字段缺失，待日志所有者补证。", "evidence_ids": ids})
    assert allowed.status_code == 200
    assert allowed.json()["decision"] == "证据不足"


def test_reset_invalidates_c_only_and_old_runs_cannot_be_replayed(client):
    run = start(client).json()
    a_run = client.post("/api/v1/a/documents/PO-A-017/identify", json={}).json()
    b_run = client.post("/api/v1/runs", json={"polluted": True}).json()
    c_reset = client.post("/api/v1/c/reset").json()
    assert c_reset["runs"] == {} and c_reset["audits"] == []
    assert client.post(f"/api/v1/c/runs/{run['id']}/analyze", json={}).status_code == 404
    assert a_run["id"] in client.get("/api/v1/a/state").json()["runs"]
    assert b_run["id"] in client.get("/api/v1/state").json()["runs"]
    assert client.get("/api/v1/c/cases").status_code == 200


def test_page_assets_and_api_errors_are_local_and_have_request_ids(client):
    for path in ("/demo/a", "/demo/b", "/demo/c", "/static/demo-c.js", "/static/demo-c.css", "/static/design-system/styles.css"):
        assert client.get(path).status_code == 200
    missing = client.post("/api/v1/c/runs", json={"case_id": "UNKNOWN"}, headers={"X-Request-ID": "bad-case-103"})
    assert missing.status_code == 404
    assert missing.json()["error"]["request_id"] == "bad-case-103"
    assert missing.headers["X-Request-ID"] == "bad-case-103"
