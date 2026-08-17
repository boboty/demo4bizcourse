# 验收用例

以下是业务方给出的验收用例，描述给定输入下接口应有的响应。

| # | 输入 | 期望输出 |
|---|---|---|
| 1 | `customerLevel=GOLD, amount=1200`，不带优惠券 | HTTP 200；`membershipDiscount=100`；`discount=100`；`finalAmount=1100` |
| 2 | `customerLevel=GOLD, amount=1000`，不带优惠券 | HTTP 200；`membershipDiscount=100` |
| 3 | `customerLevel=GOLD, amount=999`，不带优惠券 | HTTP 200；`membershipDiscount=0`；`reason="NO_DISCOUNT"` |
| 4 | `customerLevel=STANDARD, amount=600, coupon=VIP100` | HTTP 200；`couponDiscount=100`；`finalAmount=500` |
| 5 | `customerLevel=GOLD, amount=1200, coupon=VIP100` | HTTP 200；`membershipDiscount=100`；`couponDiscount=100`；`discount=200`；`finalAmount=1000` |
| 6 | `customerLevel=GOLD, amount=1200, coupon=VIP100-NO-STACK` | HTTP 200；`membershipDiscount=100`；`couponDiscount=0`；`discount=100`；`finalAmount=1100` |
| 7 | `customerLevel=PLATINUM, amount=1200, coupon=VIP100` | HTTP 422 |

每条用例都需要有对应的自动化测试提供证据，测试需可重复执行并给出确定性结果。
