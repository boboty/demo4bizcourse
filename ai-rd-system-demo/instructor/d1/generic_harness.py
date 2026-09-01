#!/usr/bin/env python3
"""D1 Harness A：只读 Generic Model / Chat Harness。

仅使用 Python 标准库访问 Responses API。源码以 Harness context 放进
instructions，用户 input 只有固定的一句话任务；不会提供工具，也不会写回工作区。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "instructor" / "baselines" / "demo12-financing"
IGNORED_PARTS = {".pytest_cache", "__pycache__"}


def source_files(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and not IGNORED_PARTS.intersection(path.parts)
    }


def digest(files: dict[str, bytes]) -> str:
    entries = [(name, hashlib.sha256(data).hexdigest()) for name, data in sorted(files.items())]
    return hashlib.sha256(json.dumps(entries, ensure_ascii=False).encode()).hexdigest()


def make_bundle() -> tuple[bytes, str]:
    entries = [
        {"path": name, "sha256": hashlib.sha256(data).hexdigest(), "content": data.decode("utf-8")}
        for name, data in sorted(source_files(BASELINE).items())
    ]
    bundle = {"version": 1, "entries": entries}
    encoded = json.dumps(bundle, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return encoded, hashlib.sha256(encoded).hexdigest()


def output_text(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        if isinstance(value.get("output_text"), str):
            found.append(value["output_text"])
        if value.get("type") in {"output_text", "text"} and isinstance(value.get("text"), str):
            found.append(value["text"])
        for child in value.values():
            found.extend(output_text(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(output_text(child))
    return found


def call_api(model: str, effort: str, task: str, bundle: bytes) -> tuple[bool, dict[str, Any], str]:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return False, {}, "OPENAI_API_KEY 未设置；未向 Responses API 发送请求"
    instructions = (
        "你处于 Generic Model / Chat Harness。你只能阅读下面的只读 source_bundle，不能调用工具、"
        "执行命令、修改文件或声称已运行测试。请基于项目上下文分析用户任务，输出实施计划、修改建议和可验证风险。\n\n"
        "READ-ONLY SOURCE_BUNDLE (JSON):\n" + bundle.decode("utf-8")
    )
    payload = {
        "model": model,
        "reasoning": {"effort": effort},
        "tools": [],
        "store": False,
        "instructions": instructions,
        "input": task,
    }
    request = urllib.request.Request(
        os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1/responses"),
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = response.read().decode("utf-8")
            parsed = json.loads(body)
            if parsed.get("error"):
                return False, parsed, f"Responses API 返回 error：{parsed['error']}"
            if parsed.get("status") not in (None, "completed"):
                return False, parsed, f"Responses API 未完成：status={parsed.get('status')}"
            return True, parsed, ""
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        return False, {}, f"HTTP {exc.code}: {detail}"
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return False, {}, f"Responses API 请求失败：{exc}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--response", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    task = args.task.read_text(encoding="utf-8").strip()
    bundle, bundle_sha = make_bundle()
    args.bundle.write_bytes(bundle)
    manifest.update({"source_bundle_sha256": bundle_sha, "source_bundle_baseline_match": True})
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    success, response, error = call_api(manifest["model"], manifest["reasoning_effort"], task, bundle)
    args.response.write_text(json.dumps(response, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    text = "\n\n".join(dict.fromkeys(output_text(response)))
    if error:
        text = error
    (args.output.parent / "proposal.md").write_text(text + "\n", encoding="utf-8")

    acceptance = subprocess.run(
        [str(ROOT / ".venv/bin/python"), str(ROOT / "instructor/d1/independent_acceptance.py"), "--workspace", str(ROOT / "workspaces/d1-harness-a"), "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        check=False,
    )
    try:
        acceptance_result = json.loads(acceptance.stdout)
    except json.JSONDecodeError:
        acceptance_result = {"passed": False, "problems": ["验收器未产生 JSON"], "boundary_violations": [], "changed_files": []}
    result = {
        "harness": "GENERIC",
        "manifest": manifest,
        "baseline_digest": digest(source_files(BASELINE)),
        "workspace_source_digest": digest(source_files(ROOT / "workspaces/d1-harness-a")),
        "first_context_reads": "source_bundle.json（冻结 baseline 的全部可见源码）",
        "plan_evidence": any(marker in text.lower() for marker in ("plan", "计划", "步骤")),
        "engineering_tools": "Responses API（tools=[]，只读）",
        "tool_capabilities": {"inspect": True, "modify": False, "commands": False, "tests": False},
        "agent_ran_dev_tests": False,
        "files_changed": [],
        "dev_test_passed": None,
        "dev_test_summary": "未执行（Harness A 无命令执行能力）",
        "independent_acceptance_passed": bool(acceptance_result.get("passed")),
        "independent_acceptance_problems": acceptance_result.get("problems", []),
        "boundary_violations": acceptance_result.get("boundary_violations", []),
        "api_success": success,
        "api_error": error,
        "proposal": text,
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"captured Generic Harness evidence: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
