# Round 6A Expected Observations

课堂记录使用“Action → Observation → Meaning”，不要只写 PASS/FAIL。

## Demo 0

| Action | Observation | Meaning |
| --- | --- | --- |
| 打开自然语言 case | 有业务步骤，但没有固定 device、facts、evidence、cleanup 契约 | 人类可读 case 不等于可执行 task |
| 打开最终 YAML | 有 device、precondition、test_data、workflow、UI、assertions、evidence、cleanup | 执行系统需要明确输入和验收边界 |

## Demo 1 TRUE_DEVICE

| Action | Observation | Meaning |
| --- | --- | --- |
| V1 baseline | physical iPhone Safari 完成登录、待付款订单、支付；API facts 通过；cleanup 通过 | Mac → Appium → XCUITest/WDA → iPhone → Safari → FastAPI 链路真实可用 |
| V2 + old locator | `pay_order` locator failure；真实 DOM 中 `#pay-now` 匹配数=0 | 不是设备失败、不是服务失败，是正式自动化资产失配 |
| Failure Bundle | 有 failure context、page source、screenshot、Appium log | 失败可以被审计，且 Self-Heal 输入有边界 |
| Candidate Review | unique match=1；Review APPROVED；固定 API facts 未改变 | AI 只提出候选，确定性 Gate 决定是否可用 |
| Candidate Verify | 3/3 PASS，包含 UI、API facts、cleanup | 候选被临时验证，不等于直接修改正式资产 |
| Write Back + AI-off rerun | 只写回 locator；不再调用 AI 也 PASS | 正式资产修改受 Gate 控制，结果可重复 |
| Restore | locator 回到 `#pay-now`；可再次制造同一 failure | 演示可复位，下一次课堂不继承污染 |

## Demo 2 PREGENERATED_REAL_RESULT

| Action | Observation | Meaning |
| --- | --- | --- |
| 展示 Round 4 summary | total=5、passed=4、failed=1；Engineering acceptance=PASS、test run=FAIL | 测试系统成功完成了一次失败的测试 |
| PRODUCT BUG facts | UI payment result=PASS；Order=PAID；Payment=1；SUCCEEDED；Inventory=10 | 页面成功不等于业务正确 |
| timeout_before_commit | HTTP 504 → query 得到 PENDING_PAY/Payment=0 → RETRY_ALLOWED → retry once | Retry 由业务提交事实决定 |
| timeout_after_commit | HTTP 504 → query 得到 PAID/Payment=1 → NO_RETRY_ALREADY_COMMITTED | 客户端没拿到成功响应不等于业务没有成功 |

## Demo 2 CONTROLLED_LOCAL_EXPERIMENT

| Action | Observation | Meaning |
| --- | --- | --- |
| Failure Classification | PRODUCT、AUTOMATION、ENVIRONMENT、DEVICE；证据不足为 UNCLASSIFIED | Cause 依赖结构化 evidence，不依赖关键词或 scenario 名称 |
| Flaky timing/wait | 12 runs，6 PASS、6 FAIL；失败均 AUTOMATION；stability=FLAKY | Flaky 描述跨运行稳定性，不是第五种 Failure Cause |
| Shared State barrier | 同一 order_id、同一 PENDING_PAY prestate；一个 committed、一个 already_paid；最终 PAID/Payment=1/Inventory=9 | 共享业务状态会破坏测试独立性，不代表数据库写坏 |
