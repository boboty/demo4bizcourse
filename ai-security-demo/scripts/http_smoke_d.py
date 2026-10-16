"""通过真实 HTTP 自检 Demo D 的本地业务链和独立重置。"""

import json
import urllib.error
import urllib.request
import uuid
from pathlib import Path

BASE = "http://127.0.0.1:8016"
TRACE: list[dict] = []


def call(method: str, path: str, body: dict | None = None, expected: int = 200) -> dict:
    request_id = f"smoke-d-{uuid.uuid4().hex[:12]}"
    request = urllib.request.Request(BASE + path, data=None if body is None else json.dumps(body, ensure_ascii=False).encode(),
        headers={"X-Request-ID": request_id, "Content-Type": "application/json"}, method=method)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
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
    TRACE.append({"method": method, "path": path, "expected_status": expected, "status": status, "request_id": request_id, "response": data})
    return data


def run() -> dict:
    health = call("GET", "/api/v1/health")
    assert health["external_services"] is False
    page = call("GET", "/demo/d")
    assert "Demo D" in page.get("html", "") if page.get("html") else True
    raw = call("GET", "/api/v1/d/logs")
    assert len(raw["items"]) == 10 and len({row["id"] for row in raw["items"]}) == 10
    initial_state = {key: call("GET", f"/api/v1/{key}/state") for key in ("a", "c")}
    initial_state["b"] = call("GET", "/api/v1/state")

    call("POST", "/api/v1/d/reset", {})
    run_data = call("POST", "/api/v1/d/runs", {}, 201)
    run_id = run_data["id"]
    call("POST", f"/api/v1/d/runs/{run_id}/explain", {}, 409)
    call("POST", f"/api/v1/d/runs/{run_id}/brief", {}, 409)
    analysis = call("POST", f"/api/v1/d/runs/{run_id}/analyze", {})
    by_rule = {row["rule_id"] for row in analysis["findings"]}
    assert {"RULE-D-AUTH-RATE", "RULE-D-OFF-HOURS", "RULE-D-REPEATED-DENY"} <= by_rule
    assert "LOG-D-004" in analysis["normal_log_ids"]
    explanation = call("POST", f"/api/v1/d/runs/{run_id}/explain", {})
    assert explanation["final_decision"] is None and explanation["inference_id"] == "INFER-D-CREDENTIAL-EXFIL-01"
    assert not set(explanation["inference_evidence_ids"]) - {row["id"] for row in raw["items"]}
    call("POST", f"/api/v1/d/runs/{run_id}/review", {"finding_id": "FAKE", "decision": "排除", "rationale": "x", "evidence_ids": ["LOG-D-006"]}, 404)
    call("POST", f"/api/v1/d/runs/{run_id}/review", {"finding_id": explanation["inference_id"], "decision": "排除", "rationale": " ", "evidence_ids": ["LOG-D-006"]}, 422)
    call("POST", f"/api/v1/d/runs/{run_id}/review", {"finding_id": explanation["inference_id"], "decision": "排除", "rationale": "unknown", "evidence_ids": ["unknown"]}, 422)
    call("POST", f"/api/v1/d/runs/{run_id}/review", {"finding_id": explanation["inference_id"], "decision": "排除", "rationale": "irrelevant", "evidence_ids": ["LOG-D-004"]}, 422)
    call("POST", f"/api/v1/d/runs/{run_id}/review", {"finding_id": explanation["inference_id"], "decision": "排除", "rationale": "forged role", "evidence_ids": ["LOG-D-006"], "role": "admin"}, 422)
    review = call("POST", f"/api/v1/d/runs/{run_id}/review", {"finding_id": explanation["inference_id"], "decision": "排除", "rationale": "原始记录仅证明有非工作时段登录；没有凭据来源、响应体积或出口流量，不能支持账号失陷和数据外传。", "evidence_ids": ["LOG-D-006"]}, 200)
    assert review["reviewer"]["id"] == "sec-reviewer-008"
    brief = call("POST", f"/api/v1/d/runs/{run_id}/brief", {})
    assert {"已证实事实", "AI 推测", "待核查", "建议动作"} <= brief.keys()
    assert brief["AI 推测"][0]["status"] == "人工核查后排除"
    assert all(item["evidence_ids"] for column in ("已证实事实", "AI 推测", "待核查", "建议动作") for item in brief[column])
    assert "不执行" in brief["建议动作"][0]["text"]
    d_state = call("GET", "/api/v1/d/state")
    run_state = d_state["runs"][run_id]
    audit = [item for item in d_state["audits"] if item["run_id"] == run_id]
    assert len(run_state["audit_ids"]) == len(set(run_state["audit_ids"])) == 5
    assert set(run_state["audit_ids"]) == {item["id"] for item in audit}
    assert all(item["run_id"] == run_id and item["object_id"] and item["request_id"] for item in audit)

    call("POST", "/api/v1/d/reset", {})
    call("POST", f"/api/v1/d/runs/{run_id}/analyze", {}, 404)
    for key, before in initial_state.items():
        after = call("GET", "/api/v1/state" if key == "b" else f"/api/v1/{key}/state")
        assert before["runs"] == after["runs"] and before["audits"] == after["audits"], f"D reset changed {key.upper()}"
    return {"result": "PASS", "request_count": len(TRACE), "trace": TRACE}


if __name__ == "__main__":
    result = run()
    output = Path(__file__).parents[2] / "evidence" / "demo-d-worker" / "http-smoke.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"result": result["result"], "request_count": result["request_count"], "evidence": str(output)}, ensure_ascii=False))
