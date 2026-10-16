import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        test_client.post("/api/v1/d/reset")
        yield test_client


def to_explained(client):
    run = client.post("/api/v1/d/runs", json={}).json()
    run_id = run["id"]
    analysis = client.post(f"/api/v1/d/runs/{run_id}/analyze", json={})
    explanation = client.post(f"/api/v1/d/runs/{run_id}/explain", json={})
    return run, analysis.json(), explanation.json()


def test_synthetic_log_set_has_stable_ids_rules_and_normal_reference_records(client):
    payload = client.get("/api/v1/d/logs").json()
    logs = payload["items"]
    assert len(logs) >= 8
    assert len({item["id"] for item in logs}) == len(logs)
    assert all(item["id"].startswith("LOG-D-") for item in logs)
    assert "合成数据" in payload["time_basis"]
    run, analysis, _ = to_explained(client)
    rules = {item["rule_id"] for item in analysis["findings"]}
    assert {"RULE-D-AUTH-RATE", "RULE-D-OFF-HOURS", "RULE-D-REPEATED-DENY"} <= rules
    service_rules = {item["rule_id"] for item in analysis["findings"] if item["account"] == "svc-report-02"}
    assert service_rules == {"RULE-D-AUTH-RATE"}
    assert "LOG-D-004" in analysis["normal_log_ids"]
    assert "误报" in analysis["scope"]
    assert run["logs"] == logs


def test_flow_requires_order_ai_claim_stays_speculative_and_human_corrects_with_evidence(client):
    run = client.post("/api/v1/d/runs", json={}).json()
    run_id = run["id"]
    assert client.post(f"/api/v1/d/runs/{run_id}/explain", json={}).status_code == 409
    assert client.post(f"/api/v1/d/runs/{run_id}/brief", json={}).status_code == 409
    assert client.post(f"/api/v1/d/runs/{run_id}/review", json={
        "finding_id": "INFER-D-CREDENTIAL-EXFIL-01", "decision": "排除", "rationale": "理由", "evidence_ids": ["LOG-D-006"]
    }).status_code == 409
    assert client.post(f"/api/v1/d/runs/{run_id}/analyze", json={}).status_code == 200
    explanation = client.post(f"/api/v1/d/runs/{run_id}/explain", json={}).json()
    assert explanation["model"].startswith("离线确定性模拟")
    assert explanation["inference_id"] == "INFER-D-CREDENTIAL-EXFIL-01"
    assert "凭据泄露" in explanation["inference"] and "没有提供" in explanation["uncertainty"]
    assert explanation["final_decision"] is None
    analysis = client.post(f"/api/v1/d/runs/{run_id}/analyze", json={})
    assert analysis.status_code == 409
    assert client.post(f"/api/v1/d/runs/{run_id}/review", json={
        "finding_id": "FAKE", "decision": "排除", "rationale": "伪造", "evidence_ids": ["LOG-D-006"]
    }).status_code == 404
    bad_role = client.post(f"/api/v1/d/runs/{run_id}/review", json={
        "finding_id": explanation["inference_id"], "decision": "排除", "rationale": "拒绝角色篡改", "evidence_ids": ["LOG-D-006"], "role": "admin"
    })
    assert bad_role.status_code == 422
    empty_rationale = client.post(f"/api/v1/d/runs/{run_id}/review", json={
        "finding_id": explanation["inference_id"], "decision": "排除", "rationale": "   ", "evidence_ids": ["LOG-D-006"]
    })
    assert empty_rationale.status_code == 422 and empty_rationale.json()["error"]["code"] == "RATIONALE_REQUIRED"
    assert client.post(f"/api/v1/d/runs/{run_id}/review", json={
        "finding_id": explanation["inference_id"], "decision": "排除", "rationale": "伪造日志", "evidence_ids": ["FAKE"]
    }).status_code == 422
    assert client.post(f"/api/v1/d/runs/{run_id}/review", json={
        "finding_id": explanation["inference_id"], "decision": "排除", "rationale": "无关日志", "evidence_ids": ["LOG-D-004"]
    }).status_code == 422
    assert client.post(f"/api/v1/d/runs/{run_id}/review", json={
        "finding_id": explanation["inference_id"], "decision": "排除", "rationale": "重复证据", "evidence_ids": ["LOG-D-006", "LOG-D-006"]
    }).status_code == 422
    review = client.post(f"/api/v1/d/runs/{run_id}/review", json={
        "finding_id": explanation["inference_id"], "decision": "排除", "rationale": "样本只有非工作时段登录记录；没有凭据来源、响应字节数或出口日志，不能支持账号失陷和数据外传。", "evidence_ids": ["LOG-D-006"]
    }, headers={"X-Request-ID": "review-d-known"})
    assert review.status_code == 200
    reviewed = review.json()
    assert reviewed["reviewer"]["role"] == "security_log_reviewer"
    assert reviewed["decision"] == "排除" and reviewed["request_id"] == "review-d-known"
    assert "不代表账号失陷" in reviewed["finding_title"] or "AI 推测" in reviewed["finding_title"]
    assert client.post(f"/api/v1/d/runs/{run_id}/brief", json={}).status_code == 200
    brief = client.get("/api/v1/d/state").json()["runs"][run_id]["brief"]
    assert {"已证实事实", "AI 推测", "待核查", "建议动作"} <= brief.keys()
    assert any("非工作时段" in item["text"] for item in brief["已证实事实"])
    assert brief["AI 推测"][0]["status"] == "人工核查后排除"
    assert all(item["evidence_ids"] for key in ("已证实事实", "AI 推测", "待核查", "建议动作") for item in brief[key])
    assert "封禁" in brief["建议动作"][0]["text"] and "不执行" in brief["建议动作"][0]["text"]
    assert "已通过 API 外传数据" not in " ".join(item["text"] for item in brief["已证实事实"])


def test_review_supports_false_positive_exclusion_and_pending_evidence(client):
    run, analysis, _ = to_explained(client)
    run_id = run["id"]
    service_finding = next(item for item in analysis["findings"] if item["account"] == "svc-report-02")
    excluded = client.post(f"/api/v1/d/runs/{run_id}/review", json={
        "finding_id": service_finding["id"], "decision": "排除", "rationale": "样本内该账号为报表服务例行登录和自动重试，需业务负责人继续确认是否属于计划任务。", "evidence_ids": service_finding["log_ids"]
    })
    assert excluded.status_code == 200

    client.post("/api/v1/d/reset")
    run, _, explanation = to_explained(client)
    pending = client.post(f"/api/v1/d/runs/{run['id']}/review", json={
        "finding_id": explanation["inference_id"], "decision": "待补证", "rationale": "缺少认证来源、响应体积和出口流量记录，补齐后再判断。", "evidence_ids": explanation["inference_evidence_ids"]
    })
    assert pending.status_code == 200
    client.post(f"/api/v1/d/runs/{run['id']}/brief", json={})
    brief = client.get("/api/v1/d/state").json()["runs"][run["id"]]["brief"]
    assert brief["AI 推测"][0]["status"] == "待补证"


def test_audit_ids_are_unique_and_reset_invalidates_only_demo_d(client):
    run, _, explanation = to_explained(client)
    run_id = run["id"]
    client.post(f"/api/v1/d/runs/{run_id}/review", json={
        "finding_id": explanation["inference_id"], "decision": "排除", "rationale": "没有外传证据。", "evidence_ids": ["LOG-D-006"]
    })
    client.post(f"/api/v1/d/runs/{run_id}/brief", json={})
    state = client.get("/api/v1/d/state").json()
    run_audits = [item for item in state["audits"] if item["run_id"] == run_id]
    run_state = state["runs"][run_id]
    assert [item["action"] for item in run_audits] == ["create_run", "deterministic_rule_analysis", "offline_assistant_analysis", "human_log_review", "generate_four_section_brief"]
    assert len(run_state["audit_ids"]) == len(set(run_state["audit_ids"])) == 5
    assert set(run_state["audit_ids"]) == {item["id"] for item in run_audits}
    assert all(item["actor_id"] == "sec-reviewer-008" and item["role"] == "security_log_reviewer" and item["object_id"] and item["request_id"] for item in run_audits)
    a_run = client.post("/api/v1/a/documents/PO-A-017/identify", json={}).json()
    b_run = client.post("/api/v1/runs", json={"polluted": True}).json()
    c_run = client.post("/api/v1/c/runs", json={"case_id": "C-CASE-101"}).json()
    reset = client.post("/api/v1/d/reset").json()
    assert reset["runs"] == {} and reset["audits"] == []
    assert client.post(f"/api/v1/d/runs/{run_id}/analyze", json={}).status_code == 404
    assert a_run["id"] in client.get("/api/v1/a/state").json()["runs"]
    assert b_run["id"] in client.get("/api/v1/state").json()["runs"]
    assert c_run["id"] in client.get("/api/v1/c/state").json()["runs"]


def test_d_page_and_validation_error_are_local_and_identifiable(client):
    for path in ("/demo/d", "/static/demo-d.js", "/static/demo-d.css", "/static/design-system/styles.css"):
        assert client.get(path).status_code == 200
    invalid = client.post("/api/v1/d/runs", json={"role": "admin"}, headers={"X-Request-ID": "d-invalid-request"})
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "INVALID_INPUT"
    assert invalid.json()["error"]["request_id"] == "d-invalid-request"
