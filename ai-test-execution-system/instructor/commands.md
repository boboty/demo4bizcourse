# Round 6A Classroom Commands

所有命令默认在 `ai-test-execution-system/` 目录执行。`<...>` 是课堂本机占位符，不应写回 Git。

| 标签 | 命令 | 用途 |
| --- | --- | --- |
| GATE | `python3 -m pytest` | 开课前确认 34 tests PASS |
| GATE | `git diff --check` | 空白和 patch 门禁 |
| RESET | `./scripts/reset_demo.sh` | 恢复 V1、normal、Product Bug off、PENDING_PAY、库存 10 |
| LIVE | `./scripts/preflight_ios.sh` | 真机/Appium/Xcode/QuickTime 前置检查 |
| LIVE | `./scripts/start_demo.sh` | 启动 FastAPI 被测系统 |
| LIVE | `DEMO_BASE_URL='http://<MAC-LAN-IP>:8000' IOS_UDID='<IPHONE-UDID>' IOS_TEAM_ID='<APPLE-TEAM-ID>' IOS_WDA_BUNDLE_ID='<PERSONAL-WDA-BUNDLE-ID>' python3 scripts/run_pay_order_ios.py` | 真机 baseline |
| LIVE | `./scripts/restore_self_heal_baseline.sh` | 恢复正式旧 locator 与 baseline |
| LIVE | `python3 scripts/run_round2_self_heal.py --stop-after-failure` | 真实 V1 → V2 old locator failure |
| LIVE | `python3 scripts/render_round2_candidate_prompt.py <failure-context> <page-source> <screenshot>` | 生成真实 Candidate 输入 |
| LIVE/FALLBACK | `python3 scripts/run_round2_self_heal.py --failure-dir <FAILURE-DIR> --interactive-candidate <REAL-CANDIDATE-JSON>` | Candidate Gate、Verify、Write Back、AI-off rerun |
| LIVE | `python3 -m experiments.failure_classification` | 短的 Round 5 分类实验 |
| OPTIONAL | `python3 -m experiments.flaky_automation` | 重新执行 12 次 controlled timing/wait |
| OPTIONAL | `python3 -m experiments.shared_state_concurrency` | 重新执行 shared-state experiment |
| FALLBACK | `cat evidence/round4-pass-summary.md` | 展示脱敏 Round 4 真实结果 |
| FALLBACK | `cat evidence/round5-pass-summary.md` | 展示脱敏 Round 5 真实结果 |
| RESET | `./scripts/restore_self_heal_baseline.sh && ./scripts/reset_demo.sh` | Demo 结束清理 |

Fallback 只使用课前保存的真实结果，不能临时编写或改写结果数字。
