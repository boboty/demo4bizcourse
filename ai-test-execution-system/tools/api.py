"""HTTP Tool：只负责发送请求并暴露明确的响应或错误。"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional


class HttpToolError(RuntimeError):
    """请求无法建立或响应无法解析。"""


@dataclass(frozen=True)
class HttpResponse:
    status_code: int
    body: Any

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300


def http_request(
    url: str, method: str = "GET", payload: Any = None, timeout: int = 90
) -> HttpResponse:
    """发送一次 HTTP 请求；不重试，不解释业务结果。"""
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return HttpResponse(response.status, json.loads(body) if body else None)
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8")
        try:
            parsed = json.loads(body) if body else None
        except json.JSONDecodeError:
            parsed = {"raw_body": body}
        return HttpResponse(error.code, parsed)
    except urllib.error.URLError as error:
        raise HttpToolError("HTTP 请求失败：{0}".format(error.reason)) from error


def get(url: str, timeout: int = 90) -> HttpResponse:
    return http_request(url, method="GET", timeout=timeout)


def post(url: str, payload: Any = None, timeout: int = 90) -> HttpResponse:
    return http_request(url, method="POST", payload=payload, timeout=timeout)


def require_success(
    url: str, method: str = "GET", payload: Any = None, timeout: int = 90
) -> Any:
    """将一次非 2xx 响应显式转换为异常；不执行重试或业务判断。"""
    response = http_request(url, method=method, payload=payload, timeout=timeout)
    if not response.ok:
        raise HttpToolError(
            "{0} {1} 失败（HTTP {2}）：{3}".format(method, url, response.status_code, response.body)
        )
    return response.body
