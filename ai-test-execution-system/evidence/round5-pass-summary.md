# Round 5 PASS 摘要（脱敏）

## Failure Cause

- PRODUCT：真实执行 UI 支付后，API facts 为 PAID、Payment=1、SUCCEEDED，但库存仍为 10；分类依据为 `failure_skill=assert_business_state`、`ui_assertion=PASS` 与实际/期望 facts mismatch。
- AUTOMATION：使用正式 task 的内存 copy，将 pay locator 改为不存在的 selector；服务、页面、设备会话均正常，locator/wait 层失败，Payment 未执行。
- ENVIRONMENT：使用受控不可访问本地端口执行 health；尚未进入业务 Workflow。
- DEVICE：服务可访问，但受控不存在的 device identifier 在 device preflight 层失败；未建立会话。
- UNCLASSIFIED：仅提供错误文本、缺少结构化阶段与设备/服务 evidence，分类器显式返回 `UNCLASSIFIED`。

Failure Cause 与 Stability 保持正交；`FLAKY` 不是第五种 Failure Cause。

## Flaky History

- 同一个 timing/wait experiment 实际执行 12 次。
- total=12，PASS=6，FAIL=6。
- FAIL category：AUTOMATION。
- minimum_samples=5，stability=`FLAKY`。
- history 使用 JSONL 保存于本机 `artifacts/history/`，未提交。

## Shared-State Concurrency

- 两个 worker 共享同一个 order state 和 order_id。
- 两个 worker 在 barrier 后执行支付；一个提交成功，另一个观察到 `already_paid`。
- 最终 facts：Order=PAID、Payment=1、库存=9。
- 结果：`STATE_CONTAMINATION_OBSERVED`。
- 实验位于 `experiments/`，没有为正式 Suite 增加 parallel 模式。

## 工程门禁

- 原 Round 4 自动测试基线：26 passed。
- Round 5 全部自动测试：34 passed。
- Round 2 Self-Heal、Round 3 Workflow、Round 4 serial Run Plan 回归：PASS。
- `git diff --check`：PASS。
- Round 5 runtime outputs 与 history：Git policy=`ignore`。

本摘要不包含设备标识、账号标识、绝对路径、session id、原始日志或截图。
