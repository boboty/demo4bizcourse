# 独立验收标准

| ID | 验收项 | 必需测试证据 |
| --- | --- | --- |
| AC-001 | 正确请求可获得结构完整的优惠预览。 | HTTP 200、`eligible`、金额和 `reason`。 |
| AC-002 | GOLD 满 1000 元可获得 100 元会员优惠。 | `membershipDiscount == 100`。 |
| AC-003 | `VIP100` 可产生 100 元券优惠。 | `couponDiscount == 100`。 |
| AC-004 | GOLD 满门槛且使用 `VIP100` 时，会员判断不得被跳过，并允许两项优惠叠加。 | 同时断言 `membershipDiscount == 100`、`couponDiscount == 100`、`discount == 200`，以及 `CHECK_GOLD_LEVEL` 和 `APPLY_GOLD_DISCOUNT` 出现在 `decisionTrace`。 |
| AC-005 | GOLD 满门槛且使用 `VIP100-NO-STACK` 时，不能因券存在而丢失会员优惠。 | `membershipDiscount == 100`、`couponDiscount == 0`、`RETAIN_GOLD_DISCOUNT` 出现在 `decisionTrace`。 |

AC-004 是本 Demo 的关键规则。只检查最终金额、HTTP 状态码或 JSON 字段存在，均不是 AC-004 的有效证据。

