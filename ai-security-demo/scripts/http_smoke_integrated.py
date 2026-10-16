"""按课堂顺序通过真实 HTTP 复演 A/B/C/D，并逐项验证独立重置。"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
import uuid
from pathlib import Path

BASE = "http://127.0.0.1:8016"
TRACE: list[dict] = []


def call(method: str, path: str, body: dict | None = None, expected: int = 200) -> dict:
    request_id = f"integration-{uuid.uuid4().hex[:12]}"
    request = urllib.request.Request(
        BASE + path,
        data=None if body is None else json.dumps(body, ensure_ascii=False).encode(),
        headers={"X-Request-ID": request_id, "Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            status, headers, content = response.status, dict(response.headers.items()), response.read().decode()
    except urllib.error.HTTPError as error:
        status, headers, content = error.code, dict(error.headers.items()), error.read().decode()
    try:
        data = json.loads(content) if content else {}
    except json.JSONDecodeError:
        data = {"html": content}
    assert status == expected, f"{method} {path}: expected {expected}, got {status}: {data}"
    normalized = {key.lower(): value for key, value in headers.items()}
    assert normalized.get("x-request-id") == request_id
    if "error" in data:
        assert data["error"]["request_id"] == request_id
    TRACE.append({"method": method, "path": path, "expected_status": expected, "status": status,
                  "request_id": request_id, "response": data})
    return data


def post(path: str, body: dict | None = None, expected: int = 200) -> dict:
    return call("POST", path, body or {}, expected)


def get(path: str) -> dict:
    return call("GET", path)


def run() -> dict:
    health = get("/api/v1/health")
    assert health["external_services"] is False
    pages = {letter: get(f"/demo/{letter}") for letter in "abcd"}
    for letter, response in pages.items():
        assert f"Demo {letter.upper()}" in response.get("html", "") if response.get("html") else True

    for endpoint in ("/api/v1/a/reset", "/api/v1/reset", "/api/v1/c/reset", "/api/v1/d/reset"):
        post(endpoint)

    # A: rules → offline false positive → evidence correction → preview → explicit human confirmation.
    a_run = post("/api/v1/a/documents/PO-A-017/identify", {}, 201)
    aid = a_run["id"]
    post(f"/api/v1/a/documents/PO-A-017/process/{aid}", {"confirmation": "CONFIRM_NEXT_STEP"}, 409)
    finding = post(f"/api/v1/a/runs/{aid}/assistant-review")
    assert finding["finding"]["evidence"] == "128000 元" and finding["finding"]["suggested_category"] == "personal"
    post(f"/api/v1/a/runs/{aid}/correction", {"evidence": "DEMO-PERSON-017", "suggested_category": "personal",
        "corrected_category": "ordinary", "reason": "无效证据测试。"}, 422)
    correction = post(f"/api/v1/a/runs/{aid}/correction", {"evidence": "128000 元", "suggested_category": "personal",
        "corrected_category": "ordinary", "reason": "合同金额不是可识别自然人的证据。"})
    assert correction["status"] == "human_corrected"
    preview = post(f"/api/v1/a/runs/{aid}/preview")
    assert preview["authorization"] == "ALLOW" and "DEMO-PERSON-017" not in preview["after"]
    post(f"/api/v1/a/documents/PO-A-017/process/{aid}", {}, 422)
    result = post(f"/api/v1/a/documents/PO-A-017/process/{aid}", {"confirmation": "CONFIRM_NEXT_STEP"})
    assert result["authorization"] == "ALLOW" and "128000 元" in result["after"]
    unapproved = post("/api/v1/a/documents/PO-A-018/identify", {}, 201)
    post(f"/api/v1/a/documents/PO-A-018/process/{unapproved['id']}", {}, 403)
    for action, payload in (("identify", {}), ("process/boundary-probe", {}), ("upload", {})):
        post(f"/api/v1/a/documents/DOC-CLASSIFIED-009/{action}", payload, 403)
    a_final = get("/api/v1/a/state")
    assert a_final["counters"] == {"identification": 2, "deidentification": 1, "upload": 0}
    assert len(a_final["audits"]) == 10

    # B: read, poisoned proposal, fault bypass, and protected denial of the same proposal.
    normal = post("/api/v1/runs", {"polluted": False}, 201)
    normal_exec = post(f"/api/v1/runs/{normal['id']}/executions", {"mode": "safe", **normal["proposal"]})
    assert normal_exec["authorization"] == "ALLOW"
    polluted = post("/api/v1/runs", {"polluted": True}, 201)
    bypass = post(f"/api/v1/runs/{polluted['id']}/executions", {"mode": "unsafe", **polluted["proposal"]})
    denied = post(f"/api/v1/runs/{polluted['id']}/executions", {"mode": "safe", **polluted["proposal"]}, 403)
    assert bypass["authorization"] == "BYPASS" and denied["authorization"] == "DENY"
    b_final = get("/api/v1/state")
    assert b_final["stores"]["unsafe"]["status"] == "已批准" and b_final["stores"]["safe"]["status"] == "待审批"

    # C: rule and simulated explanation; evidence check and human adjudication; exportable question candidate.
    c_cases = get("/api/v1/c/cases")["items"]
    assert len(c_cases) == 3
    c_case = post("/api/v1/c/runs", {"case_id": "C-CASE-102"}, 201)
    cid = c_case["id"]
    c_analysis = post(f"/api/v1/c/runs/{cid}/analyze")
    assert c_analysis["hits"]
    c_explain = post(f"/api/v1/c/runs/{cid}/explain")
    assert c_explain["final_decision"] is None
    c_questions = get(f"/api/v1/c/runs/{cid}/candidate-questions")
    assert c_questions["items"]
    c_evidence = [item["id"] for item in c_case["case"]["evidence"]]
    post(f"/api/v1/c/runs/{cid}/evidence-check", {"evidence_ids": c_evidence})
    c_review = post(f"/api/v1/c/runs/{cid}/review", {"decision": "违规", "rationale": "示例调用与准入白名单不符，已核对原始证据。", "evidence_ids": c_evidence})
    assert c_review["reviewer"]["id"] == "audit-024"

    # D: local logs, deterministic rules, inference, evidence-backed human review, and four-column brief.
    d_logs = get("/api/v1/d/logs")["items"]
    assert d_logs
    d_run = post("/api/v1/d/runs", {}, 201)
    did = d_run["id"]
    d_analysis = post(f"/api/v1/d/runs/{did}/analyze")
    assert d_analysis["findings"]
    d_explain = post(f"/api/v1/d/runs/{did}/explain")
    assert d_explain["final_decision"] is None
    d_review = post(f"/api/v1/d/runs/{did}/review", {"finding_id": d_explain["inference_id"], "decision": "排除",
        "rationale": "原始日志不能证明凭据来源或数据外传，排除越证推测。", "evidence_ids": ["LOG-D-006"]})
    assert d_review["reviewer"]["id"] == "sec-reviewer-008"
    brief = post(f"/api/v1/d/runs/{did}/brief")
    assert all(brief.get(column) for column in ("已证实事实", "AI 推测", "待核查", "建议动作"))

    # Independent reset checks: all other stored states must remain byte-equivalent.
    before = {"a": get("/api/v1/a/state"), "b": get("/api/v1/state"),
              "c": get("/api/v1/c/state"), "d": get("/api/v1/d/state")}
    reset_cases = [
        ("a", "/api/v1/a/reset", f"/api/v1/a/documents/PO-A-017/process/{aid}"),
        ("b", "/api/v1/reset", f"/api/v1/runs/{polluted['id']}/executions"),
        ("c", "/api/v1/c/reset", f"/api/v1/c/runs/{cid}/analyze"),
        ("d", "/api/v1/d/reset", f"/api/v1/d/runs/{did}/analyze"),
    ]
    state_paths = {"a": "/api/v1/a/state", "b": "/api/v1/state", "c": "/api/v1/c/state", "d": "/api/v1/d/state"}
    for current, endpoint, stale_path in reset_cases:
        post(endpoint)
        stale_body = {"confirmation": "CONFIRM_NEXT_STEP"} if current == "a" else {"mode": "unsafe", **polluted["proposal"]} if current == "b" else {}
        post(stale_path, stale_body, 404)
        after = {name: get(path) for name, path in state_paths.items()}
        assert not after[current]["runs"] and not after[current]["audits"], f"{current.upper()} reset did not clear own state"
        for other in "abcd":
            if other != current:
                assert before[other] == after[other], f"{current.upper()} reset changed {other.upper()} state"
        before = after

    final = {name: get(path) for name, path in state_paths.items()}
    assert final["a"]["runs"] == final["b"]["runs"] == final["c"]["runs"] == final["d"]["runs"] == {}
    return {"result": "PASS", "request_count": len(TRACE), "browser_pages": ["/demo/a", "/demo/b", "/demo/c", "/demo/d"], "trace": TRACE}


if __name__ == "__main__":
    result = run()
    output = Path(__file__).parents[1] / "evidence" / "integration-worker" / "http-integrated.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"result": result["result"], "request_count": result["request_count"], "evidence": str(output)}, ensure_ascii=False))
