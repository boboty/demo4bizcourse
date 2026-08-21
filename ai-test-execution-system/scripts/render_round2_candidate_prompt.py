#!/usr/bin/env python3
"""从真实 failure bundle 生成交互式 Codex 的最小 Candidate 提示词。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("failure", type=Path)
    parser.add_argument("page_source", type=Path)
    parser.add_argument("screenshot", type=Path)
    args = parser.parse_args()
    failure = json.loads(args.failure.read_text(encoding="utf-8"))
    print("将以下真实 failure context 连同截图文件提供给交互式 Codex；只要求其输出 JSON，不要其它文字。")
    print("截图：{0}".format(args.screenshot.name))
    print(json.dumps({
        "failure_step": failure["failure_step"],
        "old_locator": failure["old_locator"],
        "target_semantic": failure["target_semantic"],
        "page_source": args.page_source.read_text(encoding="utf-8"),
        "required_json_schema": {
            "target": "pay_button",
            "old_locator": failure["old_locator"],
            "candidate": {"using": "css selector", "value": "<current unique payment selector>"},
            "evidence": {"unique_match": True, "semantic_text": "<visible payment text>"},
        },
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
