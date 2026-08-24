#!/usr/bin/env python3
"""从真实 failure bundle 生成交互式 Codex 的受限 Candidate 任务。"""

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
    failure_path = args.failure.resolve()
    page_source_path = args.page_source.resolve()
    screenshot_path = args.screenshot.resolve()
    old_locator = failure["old_locator"]
    old_locator_json = json.dumps(old_locator, ensure_ascii=False, indent=2)
    print(
        """请基于本次真实 UI 自动化失败现场，生成一个受限 Repair Candidate。

请直接读取以下真实 Failure Bundle：

Failure Context:
{failure_context}

Page Source:
{page_source}

Failure Screenshot:
{screenshot}

任务：

当前失败步骤为 pay_order。

正式旧 locator 为：

{old_locator}

目标语义：
“支付当前待付款订单”

请结合 failure context、当前真实 DOM 和 failure screenshot，找到当前页面中唯一匹配该业务语义的支付按钮 locator。

生成的 JSON 顶层必须且只能包含：

{{
  "target": "pay_button",
  "old_locator": {old_locator_inline},
  "candidate": {{
    "using": "css selector",
    "value": "<current unique payment selector>"
  }},
  "evidence": {{
    "unique_match": true,
    "semantic_text": "<visible payment text>"
  }}
}}

严格限制：

1. 不修改 cases/pay_order.yaml
2. 不修改任何正式测试资产
3. 不修改业务代码
4. 不修改 API assertions
5. 不修改测试步骤
6. 不执行 writeback
7. 不执行 Self-Heal continuation
8. 不进行正式回归
9. Candidate 必须来自本次真实 Failure Bundle
10. candidate 必须在当前 DOM 中唯一匹配
11. 不输出 confidence 或额外字段

将最终纯 JSON 直接写入：

artifacts/runs/interactive/round2-candidate.json

写入后：

1. 使用 JSON parser 校验文件格式合法
2. 确认顶层只有 target、old_locator、candidate、evidence
3. 确认 old_locator 与 Failure Bundle 完全一致
4. 不再执行任何后续动作

完成后只向我报告：

Candidate: READY
文件路径：artifacts/runs/interactive/round2-candidate.json

并显示最终 JSON。
""".format(
            failure_context=failure_path,
            page_source=page_source_path,
            screenshot=screenshot_path,
            old_locator=old_locator_json,
            old_locator_inline=json.dumps(old_locator, ensure_ascii=False),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
