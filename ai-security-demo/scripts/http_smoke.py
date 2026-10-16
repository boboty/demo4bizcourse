"""对已启动的真实 HTTP 服务验证业务链；仅标准库，无 TestClient。"""

import json
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8016/api/v1/"


def call(path, data=None):
    request = urllib.request.Request(
        BASE + path,
        data=None if data is None else json.dumps(data).encode(),
        headers={"Content-Type": "application/json", "X-Request-ID": "http-smoke"},
    )
    try:
        response = urllib.request.urlopen(request)
    except urllib.error.HTTPError as exc:
        response = exc
    result = json.load(response)
    print(json.dumps({"path": path, "status": response.status, "result": result}, ensure_ascii=False))
    return response.status, result


def main():
    assert call("health")[1]["external_services"] is False
    for _ in range(2):
        call("reset", {})
        _, normal = call("runs", {"polluted": False})
        assert call(f"runs/{normal['id']}/executions", {"mode": "safe", **normal["proposal"]})[0] == 200
        _, polluted = call("runs", {"polluted": True})
        path = f"runs/{polluted['id']}/executions"
        assert call(path, {"mode": "unsafe", **polluted["proposal"]})[1]["after"]["status"] == "已批准"
        status, safe = call(path, {"mode": "safe", **polluted["proposal"]})
        assert status == 403 and safe["before"] == safe["after"]
        assert call(path, {"mode": "safe", **polluted["proposal"], "role": "admin"})[0] == 422
    call("reset", {})
    print("真实 HTTP 两轮完整复演通过；已恢复初始状态。")


if __name__ == "__main__":
    main()
