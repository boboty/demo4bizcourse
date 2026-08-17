# 人工评审：trial-1

## 独立执行结果
`python -m pytest experiments/real-generation/trial-1/generated_test_orders.py -v` → **22 passed, 0 failed**（对真实实现，非自报结果）。

## 关键判定：组合场景（GOLD+1200+VIP100）是否同函数内同时断言 membershipDiscount 与 couponDiscount？

**是。** `test_ac5_gold_1200_vip100_stacks`（第 ~130-143 行）在同一函数体内：
```python
assert body["membershipDiscount"] == 100
assert body["couponDiscount"] == 100
assert body["discount"] == 200
assert body["finalAmount"] == 1000
```
四个字段一起断言，且都是字面量比较（非套套逻辑）。

## 其它观察

- 结构清晰：`TestAcceptanceCases` 对应验收表 7 行，逐行一个测试方法；额外补了 `TestMembershipRuleBoundaries`（非 GOLD 不给会员优惠）、`TestCouponRuleWithoutMembership`（会员条件不满足时券单独生效）、`TestNoDiscountCase`、`TestInputValidation`（含负数金额、缺字段、非法枚举）、`TestDeterminism`（重复调用结果一致）。
- 有一个通用不变量断言 `assert_internal_consistency`：discount == membershipDiscount + couponDiscount，finalAmount == amount - discount，eligible == (discount > 0)——这是从需求文档的通用描述里推出来的，不是抄验收表。
- 没有发现引用只有读实现源码才能知道的信息（没有出现 decisionTrace 具体字符串、内部变量名等）；`discountSources`/`decisionTrace` 只做了类型校验，没有断言具体取值——说明它没有主动探测这两个字段的实际内容，选择了保守处理。

## 结论
组合场景断言：**命中**。
