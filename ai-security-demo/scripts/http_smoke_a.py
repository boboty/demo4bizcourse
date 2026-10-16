"""通过标准库 urllib 调用已启动服务的 Demo A 真实 HTTP 业务路径。"""

import json
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8016/api/v1/"


def call(path, data=None):
    request = urllib.request.Request(
        BASE + path,
        data=None if data is None else json.dumps(data, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json", "X-Request-ID": "demo-a-http-smoke"},
    )
    try:
        response = urllib.request.urlopen(request, timeout=5)
    except urllib.error.HTTPError as exc:
        response = exc
    result = json.load(response)
    item = {
        "path": path,
        "status": response.status,
        "request_id": response.headers.get("X-Request-ID"),
        "result": result,
    }
    print(json.dumps(item, ensure_ascii=False))
    return response.status, result


def main():
    assert call("health")[1]["external_services"] is False
    call("a/reset", {})
    status, permitted = call("a/documents/PO-A-017/identify", {})
    assert status == 201 and permitted["fields"]
    status, skipped = call("a/documents/PO-A-017/process/" + permitted["id"], {"confirmation": "CONFIRM_NEXT_STEP"})
    assert status == 409 and skipped["error"]["code"] == "HUMAN_REVIEW_REQUIRED"
    status, finding = call("a/runs/" + permitted["id"] + "/assistant-review", {})
    assert status == 200 and finding["finding"]["evidence"] == "128000 元"
    status, correction = call("a/runs/" + permitted["id"] + "/correction", {
        "evidence": "128000 元", "suggested_category": "personal",
        "corrected_category": "ordinary", "reason": "金额不是可识别自然人的证据。",
    })
    assert status == 200 and correction["status"] == "human_corrected"
    status, preview = call("a/runs/" + permitted["id"] + "/preview", {})
    assert status == 200 and preview["authorization"] == "ALLOW"
    status, redacted = call("a/documents/PO-A-017/process/" + permitted["id"], {"confirmation": "CONFIRM_NEXT_STEP"})
    assert status == 200 and redacted["authorization"] == "ALLOW"
    assert "DEMO-PERSON-017" not in redacted["after"] and "128000 元" in redacted["after"]

    status, denied = call("a/documents/PO-A-018/identify", {})
    assert status == 201 and {field["category"] for field in denied["fields"]}
    before = call("a/state")[1]["counters"]
    status, denied_result = call(f"a/documents/PO-A-018/process/{denied['id']}", {})
    assert status == 403 and denied_result["authorization"] == "DENY"
    assert call("a/state")[1]["counters"] == before

    for action, body in (
        ("identify", {}),
        ("process/forged-run", {}),
        ("upload", {}),
    ):
        route = action if action != "process" else "process/boundary-probe"
        status, result = call(f"a/documents/DOC-CLASSIFIED-009/{route}", body)
        assert status == 403 and result["error"]["code"] == "CONFIDENTIAL_BOUNDARY"
    final = call("a/state")[1]
    assert final["counters"] == {"identification": 2, "deidentification": 1, "upload": 0}
    assert len(final["audits"]) == 10

    status, malformed = call("a/documents/PO-A-017/identify", {"role": "admin", "approved": True})
    assert status == 422 and malformed["error"]["code"] == "INVALID_INPUT"
    old_id = permitted["id"]
    call("a/reset", {})
    assert call(f"a/documents/PO-A-017/process/{old_id}", {})[0] == 404

    b_run = call("runs", {"polluted": True})[1]
    call("a/reset", {})
    assert b_run["id"] in call("state")[1]["runs"]
    call("reset", {})
    call("a/reset", {})
    print("Demo A 真实 HTTP 授权、拒绝、涉密前置阻断、错误反馈及 A/B 独立重置通过；A/B 均恢复初态。")


if __name__ == "__main__":
    main()
