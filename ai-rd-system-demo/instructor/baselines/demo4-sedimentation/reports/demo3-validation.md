# Demo 3 independent validation report｜final

## First validation

Overall: `BLOCKER`

### Independent expectation
- GC-01: `FX_LOSS_PLUS_TAX_REFUND / 6200`
- GC-02: `TAX_REFUND_ONLY / 5000`
- GC-03: `TAX_REFUND_ONLY / 5000`
- GC-04: `NO_CANDIDATE / 0`

### Actual output
- GC-01: `TAX_REFUND_ONLY / 5000`
- GC-02: `TAX_REFUND_ONLY / 5000`
- GC-03: `TAX_REFUND_ONLY / 5000`
- GC-04: `NO_CANDIDATE / 0`

### Mismatch
GC-01 跳过了组合候选，直接选择退税单候选。

### Root cause classification
共同理解前提错误：实现与开发侧测试都采用了“只要退税候选存在就直接选退税”的同一理解，因此测试全绿。

## Repair and revalidation

开发侧修正实现和错误测试后，独立 Validator 使用同一份 Source of Truth 与 cases 重新验收：

- GC-01: PASS
- GC-02: PASS
- GC-03: PASS
- GC-04: PASS
- Overall: `PASS`

## Verified reusable business rule

这部分是 Demo 3 已经通过独立验收确认的业务事实，不是复盘角色自行推导的新规则：

1. 当汇损候选与退税候选同时具备资格时，先评估“汇损 + 退税”组合候选。
2. 若组合候选未被明确排除，应选择 `FX_LOSS_PLUS_TAX_REFUND`。
3. 组合候选金额 = 汇损金额 + 退税金额。
4. 只有组合候选被明确排除时，才允许回退到 `TAX_REFUND_ONLY`。
5. 如果只有退税候选具备资格，则选择 `TAX_REFUND_ONLY`。
6. 如果退税候选不具备资格，本演示数据集返回 `NO_CANDIDATE`。
