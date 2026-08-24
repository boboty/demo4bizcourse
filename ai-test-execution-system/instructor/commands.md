# 4-Demo Classroom Commands

所有命令默认在 `ai-test-execution-system/` 目录执行。`<...>` 是课堂本机占位符，不应写回 Git。每个新 Terminal 的第一条命令都是 `source .venv/bin/activate`。

| 标签 | 命令 | 用途 |
| --- | --- | --- |
| SETUP | `source .venv/bin/activate` | 新 Terminal 重新进入项目 `.venv` |
| SETUP | `python -m pip install -r requirements.txt` | 首次准备课堂 Python 环境 |
| GATE | `source .venv/bin/activate` + `python -m pytest` | 正式测试 Gate；不硬编码旧测试数量 |
| GATE | `git diff --check` | 空白和 patch 门禁 |
| RESET | `./scripts/reset_demo.sh` | 恢复 V1、normal、Product Bug off、PENDING_PAY、库存 10 |
| LIVE | `./scripts/preflight_ios.sh` | 保留的真机/Appium/Xcode/QuickTime 前置检查 |
| LIVE | `appium` | 人工观察 XCUITest Driver 真实 load；失败立即 STOP |
| LIVE | `appium driver run xcuitest open-wda` | 打开 XCUITest WebDriverAgent 工程 |
| LIVE | `lsof -nP -iTCP:8000 -sTCP:LISTEN` + `lsof -nP -iTCP:4723 -sTCP:LISTEN` | Round0 前检查端口；只定位占用进程，不盲杀 |
| LIVE | `MAC_LAN_IP='<MAC-LAN-IP>' IOS_UDID='<IPHONE-UDID>' IOS_TEAM_ID='<APPLE-TEAM-ID>' IOS_WDA_BUNDLE_ID='<PERSONAL-WDA-BUNDLE-ID>' ROUND0_WAIT_FOR_ENTER=1 python scripts/run_round0_ios.py` | Demo 1 Round0 真机 Safari 链路；讲解后按 Enter 释放 session |
| LIVE | `./scripts/reset_demo.sh` + `./scripts/start_demo.sh` | Demo 1 完成后启动 FastAPI，并供 Demo 3 使用 |
| LIVE | `curl -fsS http://127.0.0.1:8000/health` + `curl -fsS http://<MAC-LAN-IP>:8000/health` | Demo 2 启动后检查 local + LAN health |
| LIVE | `python instructor/run_api_demo.py normal` | Demo 2 API normal：reset/config/prepare/pay/facts/cleanup |
| LIVE | `python instructor/run_api_demo.py timeout-before` | Demo 2 HTTP 504、未提交、RETRY_ALLOWED、唯一 Retry |
| LIVE | `python instructor/run_api_demo.py timeout-after` | Demo 2 HTTP 504、已提交、NO_RETRY_ALREADY_COMMITTED、无第二次支付 |
| OPTIONAL | `python instructor/run_api_demo.py all` | 按 normal、timeout-before、timeout-after 顺序执行 |
| LIVE | `MAC_LAN_IP='<MAC-LAN-IP>' IOS_UDID='<IPHONE-UDID>' IOS_TEAM_ID='<APPLE-TEAM-ID>' IOS_WDA_BUNDLE_ID='<PERSONAL-WDA-BUNDLE-ID>' python scripts/run_pay_order_ios.py` | Demo 3 business baseline；失败必须 STOP |
| LIVE | `source .venv/bin/activate` + `./scripts/restore_self_heal_baseline.sh` + `MAC_LAN_IP='<MAC-LAN-IP>' IOS_UDID='<IPHONE-UDID>' IOS_TEAM_ID='<APPLE-TEAM-ID>' IOS_WDA_BUNDLE_ID='<PERSONAL-WDA-BUNDLE-ID>' python scripts/run_round2_self_heal.py --stop-after-failure` | Demo 3 02：真实 V2 old-locator Failure Bundle；必须看到 STOPPED_AFTER_REAL_FAILURE |
| LIVE | `FAILDIR=$(find evidence -maxdepth 2 -type d -name 'v2-old-locator-failure' -print | sort | tail -1); echo "$FAILDIR"; test -f "$FAILDIR/failure-context.json" && test -f "$FAILDIR/page-source.html" && test -f "$FAILDIR/failure-screenshot.png" && echo "Failure Bundle: READY"` | Demo 3 03：定位最新、完整真实 Failure Bundle；不匹配 round2-pass-summary.md |
| LIVE | `FAILDIR=$(find evidence -maxdepth 2 -type d -name 'v2-old-locator-failure' -print | sort | tail -1); PROMPT_FILE="/tmp/round2-candidate-prompt.txt"; python scripts/render_round2_candidate_prompt.py "$FAILDIR/failure-context.json" "$FAILDIR/page-source.html" "$FAILDIR/failure-screenshot.png" | tee "$PROMPT_FILE"; pbcopy < "$PROMPT_FILE"` | Demo 3 03A Generate Codex Task：生成并复制受限 Prompt；Codex 自行读取 Failure Bundle 并写 Candidate |
| LIVE | `CANDIDATE="artifacts/runs/interactive/round2-candidate.json"; test -f "$CANDIDATE" && echo "Candidate: READY"; python -m json.tool "$CANDIDATE"` | Demo 3 03B Check Candidate：只检查 Candidate READY 和 JSON 格式，不搬运 Codex 输出 |
| LIVE/FALLBACK | `FAILDIR=$(find evidence -maxdepth 2 -type d -name 'v2-old-locator-failure' -print | sort | tail -1); CANDIDATE="artifacts/runs/interactive/round2-candidate.json"; MAC_LAN_IP='<MAC-LAN-IP>' IOS_UDID='<IPHONE-UDID>' IOS_TEAM_ID='<APPLE-TEAM-ID>' IOS_WDA_BUNDLE_ID='<PERSONAL-WDA-BUNDLE-ID>' python scripts/run_round2_self_heal.py --failure-dir "$FAILDIR" --interactive-candidate "$CANDIDATE"` | Demo 3 04：Review、Verify 3/3、Write Back、AI-off rerun、restore、repeat failure |
| LIVE | `python -m experiments.failure_classification` | Demo 4 Failure Cause 短实验 |
| OPTIONAL | `python -m experiments.flaky_automation` | 按需要展示已有 Stability 实验 |
| OPTIONAL | `python -m experiments.shared_state_concurrency` | 按需要展示已有 Test Independence 实验 |
| FALLBACK | `cat evidence/round4-pass-summary.md` | 展示脱敏 Round 4 真实结果 |
| FALLBACK / EVIDENCE | `find artifacts/runs -type f -name retry_history.json -print | sort` | 定位真实 Retry History；选择 timeout_before_commit / timeout_after_commit 对应文件 |
| RESET | `./scripts/restore_self_heal_baseline.sh` + `./scripts/reset_demo.sh` | 安全复位 / 中断恢复；不是 AI-off rerun evidence，也不是 Self-Heal 主链 |

`instructor/run_api_demo.py` 的课堂 runtime artifact 位于被忽略的 `artifacts/runs/api-demo/`，不提交原始运行数据。Fallback 只使用课前保存的真实结果，不能临时编写 Candidate 或改写结果数字。
