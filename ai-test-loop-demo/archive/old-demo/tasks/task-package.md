# 任务包：验证订单优惠资格接口

## 目标

验证 `POST /api/orders/discount-preview` 满足订单优惠业务需求，并提供可审计的测试证据。

## 输入

- `business/requirement.md`
- `business/acceptance.md`
- `api/openapi.yaml`
- 本地 FastAPI 测试环境

## 任务

1. 分析业务规则与 OpenAPI；
2. 提取正常、异常、边界和关键业务测试点；
3. 生成 pytest 测试；
4. 执行测试并保存报告；
5. 输出每项 AC 的覆盖声明和可检验的业务断言；
6. 接受独立验收，不以生成者自己的绿灯作为结论。

## 验收标准

必须覆盖 `AC-001` 至 `AC-005`，以 `business/acceptance.md` 为准；其中 AC-004 与 AC-005 要验证 `membershipDiscount` 和 `decisionTrace`，不接受只验证 HTTP 200 或最终金额。

## 边界

- 不得修改 `business/requirement.md` 或 `business/acceptance.md`；
- 不调用在线 LLM、外部 API 或数据库；
- 测试和证据必须可本地重复执行。

## 输出

- pytest 测试；
- 测试报告；
- AC 覆盖声明；
- 可供独立验收程序读取的业务断言。

