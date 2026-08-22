# Round 6A Classroom Runbook

目标是让讲师按固定路径操作并观察判断，不需要重新理解 Round 1–5 代码。课堂只做三个 Demo；本 Runbook 不新增测试能力、不改变 task、Suite、Failure taxonomy 或 Flaky 判据。

## 开课前固定动作

```bash
cd ai-test-execution-system
python3 -m pytest                 # Gate：34 passed
git diff --check
./scripts/reset_demo.sh
```

真机 Demo 还必须完成 [`classroom-preflight.md`](classroom-preflight.md)。任何 baseline 未通过，都停止进入 Route C。

## Demo 0：从测试用例到可执行任务（5–8 分钟）

证据级别：`STATIC_ASSET`。不需要现场调用 AI。

| 步骤 | 讲师操作 | 讲师说的判断 | 学员应看到 |
| --- | --- | --- | --- |
| 1 | 打开 `demo0/natural_case.txt` | 人类描述说明测什么，但没有完整执行契约 | 自然语言步骤和业务意图 |
| 2 | 打开 `demo0/ai_draft_pay_order.yaml` | AI draft 可能有结构，但要经过 review，不能直接视为可执行资产 | 缺失或待确认的字段 |
| 3 | 打开 `demo0/review_notes.md` | 验收责任在确定性 review，不在“看起来合理” | 缺失字段、风险和修订点 |
| 4 | 打开 `cases/pay_order.yaml` | 最终 task 明确 device、precondition、test data、workflow、UI、assertions、evidence、cleanup | 完整 version 1 task |
| 5 | 打开 `docs/executable-task-schema-v1.md` | schema 冻结后，AI 不得自行改固定业务事实和 workflow | 字段契约和不可修改项 |

课堂钉子：测试用例描述测什么；可执行任务还必须说明在什么状态下、怎么做、怎么判断、失败后留下什么。

Fallback：直接打开以上文件和 `evidence/round3-pass-summary.md`，不要现场生成新的 YAML。

## Demo 1：真机 UI + Route C（20–25 分钟）

证据级别：`TRUE_DEVICE`。这部分区分 LIVE 与 fallback；fallback 必须标明“预先保存的真实结果”。

### A. 真机 baseline（LIVE）

终端 1：

```bash
cd ai-test-execution-system
./scripts/reset_demo.sh
./scripts/start_demo.sh
```

终端 2：使用课堂环境变量占位符，不把 UDID、Team ID 或 LAN IP 写入 YAML/Git：

```bash
cd ai-test-execution-system
DEMO_BASE_URL='http://<MAC-LAN-IP>:8000' \
IOS_UDID='<IPHONE-UDID>' IOS_TEAM_ID='<APPLE-TEAM-ID>' \
IOS_WDA_BUNDLE_ID='<PERSONAL-WDA-BUNDLE-ID>' \
python3 scripts/run_pay_order_ios.py
```

屏幕关注点：Appium/XCUITest 建立 session；iPhone 关注 Safari 中登录、待付款订单、支付成功；最终观察 API facts 与 cleanup。baseline 失败时停止，不允许继续 V2。

### B–C. 制造 V2 变化和旧 locator failure（LIVE）

先确认正式资产恢复为旧 locator：

```bash
./scripts/restore_self_heal_baseline.sh
python3 scripts/run_round2_self_heal.py --stop-after-failure
```

该命令先跑 V1 baseline，再切到 V2 并使用正式 `#pay-now` 制造真实失败。屏幕关注 Failure Bundle；iPhone 关注页面没有旧按钮。必须看到：`failure_step=pay_order`、真实 page source 中 `#pay-now` 匹配数为 0、结果为 `EXPECTED_LOCATOR_FAILURE`。若没有建立真机 session、没有真实 page source 或匹配数不是 0，判定为执行失败，不进入 Self-Heal。

### D–H. Candidate、Review、Verify、Write Back

从命令输出取得本次 failure bundle 路径，生成给交互式 Codex 的最小输入：

```bash
python3 scripts/render_round2_candidate_prompt.py \
  <FAILURE-DIR>/failure-context.json \
  <FAILURE-DIR>/page-source.html \
  <FAILURE-DIR>/failure-screenshot.png
```

LIVE：Candidate 由交互式 Codex 真实产生时，只保存规定 JSON；随后继续：

```bash
python3 scripts/run_round2_self_heal.py \
  --failure-dir <FAILURE-DIR> \
  --interactive-candidate <REAL-CANDIDATE-JSON>
```

Fallback：如果网络或 AI 响应不可用，展示课前保存的真实 Candidate、Review、3/3 Verify 和 Write Back evidence，并明确说“这是预先保存的真实 Candidate/结果，不是假造结果”；不得临时编写一个看似合理的 locator。

观察点：Candidate 只能进入确定性 Review；unique DOM match=1；Verify=3/3；只允许写回 pay locator；固定 API facts 不变。

### I–J. AI-off rerun 与 restore（LIVE 优先）

脚本会在 Gate + Verify 后用正式资产执行 V2 rerun，并最终恢复 baseline、再次制造旧 locator failure。课堂必须指出：最终 rerun 不调用 AI；恢复时机是 Demo 结束或任何中断后。

```bash
./scripts/restore_self_heal_baseline.sh
./scripts/reset_demo.sh
```

Fallback：展示 `evidence/round2-pass-summary.md` 和本机真实 failure bundle；不要把 fallback 说成当前现场真机执行。

## Demo 2：从一个 case 到可信执行系统（约 20 分钟）

主要展示，不现场完整重跑 5 个真机 scenario。

### 展示顺序

1. `cases/pay_order.yaml`：固定 task。
2. `suites/nightly.yaml`：单一 serial Suite。
3. `schedules/nightly.yaml`：显式 serial Run Plan。
4. `evidence/round4-pass-summary.md`：脱敏真实结果，total=5、passed=4、failed=1。
5. 本机 `reports/<run-id>/report.md` 和 `artifacts/runs/<run-id>/cases/product_bug_inventory_not_decremented/`：展示 PRODUCT BUG facts；不从 GitHub 取原始产物。
6. before/after commit 的 `retry_history.json`：说明业务语义 Retry。
7. `experiments/failure_classification.py`：展示四类分类与 UNCLASSIFIED。
8. `artifacts/round5/flaky-automation/summary.json` 与 `artifacts/history/flaky_automation.jsonl`：展示 12/6/6 和 FLAKY。
9. `artifacts/round5/shared-state-concurrency/summary.json`：展示 shared order、worker timeline 和状态污染。

### 课堂现场动作

推荐 LIVE 做一个短实验：

```bash
python3 -m experiments.failure_classification
```

Fallback：展示本机已保存的 Round 5 summary。不要现场连续重跑完整 iPhone Suite。

课堂判断顺序：Case → Suite → Run Plan → Evidence → Report → Failure Cause → Stability → Test Independence。

## Demo 后 reset

```bash
./scripts/restore_self_heal_baseline.sh
./scripts/reset_demo.sh
```

关闭 FastAPI/Appium/QuickTime 进程；保留本机 ignored evidence 供课后核验。不得把原始日志、截图、设备信息或 history 加入 Git。
