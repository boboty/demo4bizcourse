# D0 预跑稳定性报告

- 预跑次数：10
- 完整链路（先读项目 → 看到真实失败 → 修改 → 复跑转绿）：10/10
- 单次耗时：min 35.9s / max 64.3s / avg 46.6s

| run | 状态 | 耗时(s) | 实际链路 | 先读项目 | 看到失败 | 改后转绿 | 改动测试 | 最终测试 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| run-01 | COMPLETED | 38.618 | Run(FAIL) → Read/Search → Edit → Run(PASS) | True | True | True | False | 8 passed in 0.11s |
| run-02 | COMPLETED | 37.136 | Run(FAIL) → Read/Search → Edit → Run(PASS) | True | True | True | False | 8 passed in 0.15s |
| run-03 | COMPLETED | 46.518 | Run(FAIL) → Read/Search → Edit → Run(PASS) | True | True | True | False | 8 passed in 0.12s |
| run-04 | COMPLETED | 35.915 | Run(FAIL) → Read/Search → Edit → Run(PASS) | True | True | True | False | 8 passed in 0.11s |
| run-05 | COMPLETED | 57.112 | Run(FAIL) → Read/Search → Edit → Run(PASS) | True | True | True | False | 8 passed in 0.12s |
| run-06 | COMPLETED | 40.284 | Run(FAIL) → Read/Search → Edit → Run(PASS) | True | True | True | False | 8 passed in 0.11s |
| run-07 | COMPLETED | 64.266 | Run(FAIL) → Read/Search → Edit → Run(PASS) | True | True | True | False | 8 passed in 0.13s |
| run-08 | COMPLETED | 51.176 | Run(FAIL) → Read/Search → Edit → Run(PASS) → Shell | True | True | True | False | 8 passed in 0.11s |
| run-09 | COMPLETED | 42.683 | Run(FAIL) → Read/Search → Edit → Run(PASS) | True | True | True | False | 8 passed in 0.11s |
| run-10 | COMPLETED | 52.083 | Run(FAIL) → Read/Search → Edit → Run(PASS) → Shell | True | True | True | False | 8 passed in 0.12s |


## 预跑环境

- 日期：2026-09-13
- Agent：Codex CLI 0.154.0，`codex exec --json --ephemeral --sandbox workspace-write`，使用本机已登录配置（`model = gpt-5.6-sol`，`model_reasoning_effort = low`），未做任何课堂专用调参。
- 每次预跑都先 `./scripts/reset_d0.sh` 回到同一个冻结 baseline，再用同一份 `instructor/d0/task.txt`。
- 原始轨迹、diff 与逐次 `result.json` 在 `instructor/d0/preruns/`（已 gitignore）；本次冻结的成功运行在 `instructor/d0/fallback/`。
- 复现命令：`./scripts/d0_prerun.sh 10 && .venv/bin/python instructor/d0/prerun_report.py`

## 稳定性观察

1. **10/10 出现同一条链路**：`Run(FAIL) → Read/Search → Edit → Run(PASS)`。没有一次跳过验证直接改代码，也没有一次靠改测试变绿。
2. **方差主要来自耗时**（35.9s–64.3s，avg 46.6s），动作序列本身零方差。run-08 和 run-10 在 PASS 之后多了一条只读的 `Shell` 动作（收尾确认），不影响链路。
3. **修复方式有正常差异，但不影响验收**：6 次把尾差放在最后一期（`installments[-1] = total - per*(n-1)`），另外几次用列表推导或重新构造。测试断言的是"合计等于放款金额 + 每期两位小数 + 非正期数报错"这个不变式，而不是某一种分配方式，所以两种合理修法都能通过。
4. **改动边界 10/10 收敛**：每次都只改 `app/repayment/service.py`，`tests_modified` 全部为 `false`，`files_changed` 没有出现过测试文件或配置文件。
5. **没有出现随机翻车因素**：不依赖网络、不依赖随机数据、不依赖当前时间，失败在基线里是确定性的（同一份数据、同一份测试，本机重复运行结果完全一致）。

## 未验证项

- 未用 Claude Code 的 `--print` 模式做完整预跑。实测它能在 D0 里读代码、正确改代码，但无人值守模式下 Bash 需要逐次授权，Agent 会报告 pytest 被权限拦下并跳过验证——那正好破坏 D0 唯一要证明的东西。课堂使用 Claude Code 请走交互会话，见 `D0-RUNBOOK.md` 兜底一节。
- 上述 10 次预跑全部在本机同一台机器、同一次登录会话内完成；换机器或换模型后建议至少再跑 3 次确认。
