"""真实 HTTP 课堂流程自检；所有请求只访问本机虚构演示服务。"""

import json
import urllib.error
import urllib.request
import uuid
from pathlib import Path

BASE = "http://127.0.0.1:8016"
TRACE: list[dict] = []


def call(method: str, path: str, body: dict | None = None, expected: int = 200) -> dict:
    request_id = f"smoke-c-{uuid.uuid4().hex[:12]}"
    payload = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        BASE + path,
        data=payload,
        headers={"X-Request-ID": request_id, "Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            status = response.status
            headers = dict(response.headers.items())
            content = response.read().decode()
    except urllib.error.HTTPError as error:
        status = error.code
        headers = dict(error.headers.items())
        content = error.read().decode()
    data = json.loads(content) if content else {}
    assert status == expected, f"{method} {path}: expected {expected}, got {status}: {data}"
    normalized_headers = {key.lower(): value for key, value in headers.items()}
    assert normalized_headers.get("x-request-id") == request_id
    if "error" in data:
        assert data["error"]["request_id"] == request_id
    TRACE.append({"method": method, "path": path, "expected_status": expected, "status": status,
                  "request_id": request_id, "response": data})
    return data


def run() -> dict:
    call("GET", "/api/v1/health")
    cases = call("GET", "/api/v1/c/cases")["items"]
    assert len(cases) == 3
    blocked = call("POST", "/api/v1/c/runs", {"case_id": "C-CASE-101"}, 201)
    call("POST", f"/api/v1/c/runs/{blocked['id']}/explain", {}, 409)
    normal = call("POST", "/api/v1/c/runs", {"case_id": "C-CASE-101"}, 201)
    whitelist = next(item for item in normal["case"]["evidence"] if item["id"] == "EVC-C-WHITELIST-01")
    assert whitelist["title"].endswith("LIST-AI-TOOL-01 v1.0")
    call("POST", f"/api/v1/c/runs/{normal['id']}/analyze", {})
    explain = call("POST", f"/api/v1/c/runs/{normal['id']}/explain", {})
    assert explain["final_decision"] is None
    evidence_ids = [item["id"] for item in normal["case"]["evidence"]]
    call("POST", f"/api/v1/c/runs/{normal['id']}/evidence-check", {"evidence_ids": evidence_ids})
    review = call("POST", f"/api/v1/c/runs/{normal['id']}/review",
                  {"decision": "不违规", "rationale": "演示审批、日志与条文彼此吻合。", "evidence_ids": evidence_ids})
    assert review["reviewer"]["id"] == "audit-024"
    review_state = call("GET", "/api/v1/c/state")
    normal_state = review_state["runs"][normal["id"]]
    normal_audits = [item for item in review_state["audits"] if item["run_id"] == normal["id"]]
    assert len(normal_state["audit_ids"]) == 5 == len(set(normal_state["audit_ids"]))
    assert set(normal_state["audit_ids"]) == {item["id"] for item in normal_audits}
    risk = call("POST", "/api/v1/c/runs", {"case_id": "C-CASE-102"}, 201)
    analysis = call("POST", f"/api/v1/c/runs/{risk['id']}/analyze", {})
    assert len(analysis["hits"]) >= 5
    allowlist_hit = next(hit for hit in analysis["hits"] if hit["rule_id"] == "RULE-C-TOOL-ALLOWLIST")
    assert allowlist_hit["evidence"]["whitelist_id"] == "LIST-AI-TOOL-01"
    assert "EVC-C-WHITELIST-01" in allowlist_hit["source_evidence_ids"]
    questions = call("GET", f"/api/v1/c/runs/{risk['id']}/candidate-questions")
    assert questions["items"] and all(item["status"] == "待核实" for item in questions["items"])
    exported_question = next(item for item in questions["items"] if item["question_id"] == "Q-RULE-C-TOOL-ALLOWLIST")
    assert "EVC-C-WHITELIST-01" in exported_question["evidence_links"]
    insufficient = call("POST", "/api/v1/c/runs", {"case_id": "C-CASE-103"}, 201)
    analysis = call("POST", f"/api/v1/c/runs/{insufficient['id']}/analyze", {})
    assert analysis["status"] == "evidence_needed"
    call("POST", f"/api/v1/c/runs/{insufficient['id']}/explain", {})
    ids = [item["id"] for item in insufficient["case"]["evidence"]]
    call("POST", f"/api/v1/c/runs/{insufficient['id']}/evidence-check", {"evidence_ids": ids})
    call("POST", f"/api/v1/c/runs/{insufficient['id']}/review",
         {"decision": "不违规", "rationale": "不完整线索", "evidence_ids": ids}, 409)
    call("POST", f"/api/v1/c/runs/{insufficient['id']}/review",
         {"decision": "证据不足", "rationale": "用途与保留字段缺失，需补充日志。", "evidence_ids": ids})
    a_run = call("POST", "/api/v1/a/documents/PO-A-017/identify", {}, 201)
    b_run = call("POST", "/api/v1/runs", {"polluted": True}, 201)
    before_a = call("GET", "/api/v1/a/state")
    before_b = call("GET", "/api/v1/state")
    call("POST", "/api/v1/c/reset", {})
    call("POST", f"/api/v1/c/runs/{normal['id']}/analyze", {}, 404)
    after_a = call("GET", "/api/v1/a/state")
    after_b = call("GET", "/api/v1/state")
    assert before_a["runs"] == after_a["runs"] and before_a["audits"] == after_a["audits"]
    assert before_b["runs"] == after_b["runs"] and before_b["audits"] == after_b["audits"]
    assert a_run["id"] in after_a["runs"] and b_run["id"] in after_b["runs"]
    call("POST", "/api/v1/a/reset", {})
    call("POST", "/api/v1/reset", {})
    return {"result": "PASS", "request_count": len(TRACE), "trace": TRACE}


if __name__ == "__main__":
    result = run()
    output = Path(__file__).parents[1] / "evidence" / "demo-c-worker-r2" / "http-smoke.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"result": result["result"], "request_count": result["request_count"], "evidence": str(output)}, ensure_ascii=False))
