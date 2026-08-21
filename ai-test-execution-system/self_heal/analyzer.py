"""仅将真实故障上下文交给模型，生成一个受限 Repair Candidate。"""

from __future__ import annotations

import argparse
import base64
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from self_heal.candidate import Locator, RepairCandidate, save_candidate


MODEL_ENDPOINT = "https://api.openai.com/v1/responses"
DEFAULT_MODEL = "gpt-4o"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def candidate_schema() -> Dict[str, Any]:
    locator = {
        "type": "object",
        "additionalProperties": False,
        "properties": {"using": {"type": "string"}, "value": {"type": "string"}},
        "required": ["using", "value"],
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "target": {"type": "string"},
            "old_locator": locator,
            "candidate": locator,
            "evidence": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "unique_match": {"type": "boolean"},
                    "semantic_text": {"type": "string"},
                },
                "required": ["unique_match", "semantic_text"],
            },
        },
        "required": ["target", "old_locator", "candidate", "evidence"],
    }


def _response_text(response: Dict[str, Any]) -> str:
    if isinstance(response.get("output_text"), str):
        return response["output_text"]
    for output in response.get("output", []):
        for content in output.get("content", []):
            if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                return content["text"]
    raise RuntimeError("模型响应中没有结构化文本输出。")


def build_request(failure: Dict[str, Any], page_source: str, screenshot: Path, model: str) -> Dict[str, Any]:
    if not screenshot.is_file():
        raise FileNotFoundError("缺少真实 failure screenshot：{0}".format(screenshot))
    image_data = base64.b64encode(screenshot.read_bytes()).decode("ascii")
    context = {
        "failure_step": failure["failure_step"],
        "old_locator": failure["old_locator"],
        "target_semantic": failure["target_semantic"],
        "page_source": page_source,
    }
    instruction = (
        "你是 UI locator 修复分析器。只根据以下真实失败上下文与截图，输出一个 JSON Repair Candidate。"
        "不得提出修改业务步骤、API 断言、应用代码或重试；不得输出 confidence。"
        "target 必须为 pay_button，old_locator 必须逐字复述输入；candidate 使用 css selector，"
        "并且仅在当前 DOM 中唯一匹配支付当前待付款订单的按钮。\n\n"
        + json.dumps(context, ensure_ascii=False)
    )
    return {
        "model": model,
        "store": False,
        "input": [{
            "role": "user",
            "content": [
                {"type": "input_text", "text": instruction},
                {"type": "input_image", "image_url": "data:image/png;base64," + image_data},
            ],
        }],
        "text": {"format": {"type": "json_schema", "name": "repair_candidate", "strict": True, "schema": candidate_schema()}},
    }


def generate_candidate(failure_path: Path, page_source_path: Path, screenshot_path: Path, output_path: Path) -> RepairCandidate:
    """调用真实模型 API；没有 Key 或响应异常即失败，绝不伪造/降级候选。"""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("未设置 OPENAI_API_KEY；Round 2 要求真实 AI Candidate，不能使用本地 fallback。")
    failure = json.loads(failure_path.read_text(encoding="utf-8"))
    for field in ("failure_step", "old_locator", "target_semantic"):
        if field not in failure:
            raise ValueError("failure bundle 缺少字段：{0}".format(field))
    page_source = page_source_path.read_text(encoding="utf-8")
    model = os.environ.get("OPENAI_MODEL", DEFAULT_MODEL)
    request_body = build_request(failure, page_source, screenshot_path, model)
    request = urllib.request.Request(
        MODEL_ENDPOINT,
        data=json.dumps(request_body).encode("utf-8"),
        method="POST",
        headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            response_body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raise RuntimeError("OpenAI Responses API 失败（HTTP {0}）：{1}".format(error.code, error.read().decode("utf-8"))) from error
    except urllib.error.URLError as error:
        raise RuntimeError("无法调用 OpenAI Responses API：{0}".format(error.reason)) from error
    model_value = json.loads(_response_text(response_body))
    model_candidate = RepairCandidate.from_dict({
        **model_value,
        "provenance": {
            "kind": "openai_responses_api",
            "model": model,
            "response_id": response_body.get("id", "unknown"),
            "generated_at": utc_now(),
        },
    })
    save_candidate(model_candidate, output_path)
    return model_candidate


def import_interactive_candidate(raw_candidate_path: Path, failure_path: Path, output_path: Path) -> RepairCandidate:
    """导入讲师从交互式 Codex 复制的真实候选，绝不标记为 API 生成。"""
    raw = json.loads(raw_candidate_path.read_text(encoding="utf-8"))
    failure = json.loads(failure_path.read_text(encoding="utf-8"))
    required = {"target", "old_locator", "candidate", "evidence"}
    if set(raw) != required:
        raise ValueError("交互式 Candidate 必须只包含 target、old_locator、candidate、evidence。")
    if raw["old_locator"] != failure["old_locator"]:
        raise ValueError("交互式 Candidate old_locator 与真实 failure bundle 不一致。")
    candidate = RepairCandidate.from_dict({
        **raw,
        "provenance": {
            "kind": "interactive_codex_export",
            "generated_at": utc_now(),
            "source_note": "由讲师基于本次真实 failure context 与截图，在交互式 Codex 中生成后手工导入；并非 OpenAI API 实时调用。",
        },
    })
    save_candidate(candidate, output_path)
    return candidate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("failure", type=Path)
    parser.add_argument("page_source", type=Path)
    parser.add_argument("screenshot", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--interactive-candidate", type=Path, help="交互式 Codex 真实生成后手工保存的 JSON；不会伪装为 API。")
    args = parser.parse_args()
    candidate = (
        import_interactive_candidate(args.interactive_candidate, args.failure, args.output)
        if args.interactive_candidate
        else generate_candidate(args.failure, args.page_source, args.screenshot, args.output)
    )
    print(json.dumps(candidate.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
