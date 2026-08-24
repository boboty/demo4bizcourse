#!/usr/bin/env python3
"""为交互式 Codex 生成 Test Run Analysis 任务，不执行测试或调用模型。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.find_latest_complete_run import is_complete_run


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path, help="由 find_latest_complete_run.py 定位的完整 Run 目录。")
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    project_root = run_dir.parents[2]
    reports_root = project_root / "reports"
    if not is_complete_run(run_dir, reports_root):
        parser.error("Run 不是完整的真实运行，拒绝生成分析任务：{0}".format(run_dir))

    run = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    report_path = reports_root / run_dir.name / "report.md"
    analysis_path = run_dir / "agent-analysis.md"
    rules = [
        project_root / "runner" / "failure_classifier.py",
        project_root / "runner" / "retry_policy.py",
        project_root / "runner" / "stability.py",
    ]
    print(
        """请分析本仓库最近一次完整 Nightly Test Run。

你不是重新执行测试，而是分析已经产生的真实运行证据。

Run ID:
{run_id}

请读取：

- {run_json}
- {run_plan}
- {report}
- {scenario_root} 下所有 scenario result、api facts、retry history 和 evidence
- 必要时读取已有确定性能力：
  - {failure_classifier}
  - {retry_policy}
  - {stability}

任务：

1. 判断本次 Run 是否完整执行结束
2. 找出所有 FAIL scenario
3. 对每一个 FAIL 给出 Failure Cause、支撑该判断的 Evidence、Retry Decision 和 Recommended Action
4. 明确区分 Engineering / execution 是否正常完成，以及 Test Run Result 是 PASS 还是 FAIL
5. 不得因为存在 FAIL 就判断“测试系统执行失败”
6. 如果是产品 Bug，不要建议盲目 Retry
7. 如果涉及 timeout，必须依据业务事实区分 timeout_before_commit 与 timeout_after_commit
8. 如果需要 Stability 判断，使用仓库已有 Stability 判据，不自行发明
9. 优先使用仓库现有确定性分类、Retry、Stability 能力
10. 不修改任何正式测试资产
11. 不修改 Case / Suite / Run Plan
12. 不重新执行测试
13. 不修改业务代码
14. 不调用 Self-Heal
15. 不伪造缺失 Evidence

最终生成：

{analysis_path}

文件必须至少包含：

# Test Run Analysis

## Run Summary
- Run ID
- Run Completed: YES / NO
- Engineering Execution: PASS / FAIL
- Test Run Result: PASS / FAIL
- Total
- Passed
- Failed

## Failed Scenarios

对每个失败场景列出：
- Scenario
- Failure Cause
- Evidence
- Retry Decision
- Recommended Action

## Final Judgment

最后明确回答：

“这次测试执行系统是否正常完成？”
“这次测试结果是否通过？”

直接写入上述 Markdown 文件。写入后自行检查文件存在和 Markdown 内容完整，停止后续测试、写回或修复动作。

完成后只向我报告：

Agent Analysis: READY
文件路径：{analysis_path}
""".format(
            run_id=run.get("run_id", run_dir.name),
            run_json=run_dir / "run.json",
            run_plan=run_dir / "run-plan.json",
            report=report_path,
            scenario_root=run_dir / "cases",
            failure_classifier=rules[0],
            retry_policy=rules[1],
            stability=rules[2],
            analysis_path=analysis_path,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
