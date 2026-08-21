# 可执行任务 Schema v1

本文件冻结 Round 3 的第一版可执行任务契约。`cases/pay_order.yaml` 是真实执行入口，后续轮次应在这个结构上演进，不在运行时重新解释或生成任务。

## 顶层结构

```yaml
version: 1
case_id: string
title: string
device: object
preconditions: object
configuration: object
test_data: object
workflow: object
ui: object
assertions: object
evidence: object
cleanup: object
```

## 字段契约

| 字段 | 必填 | 来源/参数化 | 约束 |
| --- | --- | --- | --- |
| `version` | 是 | 任务资产 | 固定为 `1` |
| `case_id`、`title` | 是 | 任务资产 | 标识任务，不由 AI 运行时改写 |
| `device.physical`、`device.platform`、`device.browser` | 是 | 任务资产 | 本轮固定为 `true`、`iOS`、`Safari` |
| `device.*_environment` | 是 | 本机运行环境 | 只存环境变量名；UDID、Team ID、Bundle ID 不得写入 YAML |
| `preconditions.health_endpoint` | 是 | 任务资产 | 被测系统可访问性检查入口 |
| `preconditions.test_username` | 是 | 任务资产，可在本机替换 | 本轮固定测试账号语义；账号秘密不得写入证据 |
| `configuration` | 是 | 任务资产/显式执行覆盖 | 本轮为 `ui_version`、`payment_mode`、`product_bug_mode`；不得隐式重试或改变 |
| `test_data` | 是 | 任务资产 | 准备、订单事实查询和响应字段；`PENDING_PAY`、Payment=0、库存=10 由 Skill 验证 |
| `workflow.name`、`workflow.steps` | 是 | 任务资产 | 固定为 `pay_order_and_verify` 及六步顺序 |
| `ui.steps` | 是 | 任务资产 | 只描述 UI 原子动作与 locator；本轮只允许登录、打开待付款订单、支付三段动作 |
| `assertions.ui` | 是 | 任务资产 | `pay_order` 的页面结果断言；只证明 UI 结果 |
| `assertions.api_facts` | 是 | 固定验收标准 | 必须独立验证 `PAID`、Payment=1、`SUCCEEDED`、库存=9 四项事实 |
| `evidence` | 是 | 任务资产 | 截图、Appium 日志、运行上下文的文件名 |
| `cleanup` | 是 | 固定 cleanup 契约 | 必须恢复 `PENDING_PAY`、Payment=0、库存=10 并验证 |

## 固定不可修改项

执行时 AI 或 runner 不得自行修改：

- `workflow.steps` 的顺序和业务语义；
- `assertions.api_facts.equals` 四项固定事实；
- `cleanup.expected_facts`；
- UI 动作数量、动作类型和非目标 locator；
- `device` 的真机目标约束；
- 不得添加 retry、timeout 业务重试、fallback locator 或自由规划步骤。

Round 2 Self-Heal 通过既有 Gate 和真实验证后，只允许按其原有审计流程替换 `ui.steps` 中 `pay_order` 的一个 locator；这不是 Round 3 Workflow 的自由修改能力。

任务加载阶段会强校验上述冻结项：执行目标必须为 physical iOS Safari，Workflow 必须为固定六步，cleanup baseline 必须为 `PENDING_PAY`、Payment=0、库存=10；不符合时 `read_case()` 直接拒绝任务。

## 运行时输出

设备标识、签名信息、Appium 日志路径和原始截图只来自本机运行环境及 `evidence` 目录，不进入任务资产或脱敏摘要。Workflow 上下文可传递 `order_id`、`user`、设备 session 和 evidence 路径，但不得改变上述契约。
