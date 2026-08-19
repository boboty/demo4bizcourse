# 人工评审：trial-6

## 独立执行结果
`python -m pytest experiments/real-generation/trial-6/generated_test_orders.py -v` → **26 passed, 0 failed**。

## 关键判定

**命中。** `test_ac_5_gold_with_vip100_coupon_stacks`：
```python
assert body["membershipDiscount"] == 100
assert body["couponDiscount"] == 100
assert body["discount"] == 200
assert body["finalAmount"] == 1000
```

## 其它观察

- 一个值得记录的小失误（不影响本判定，但说明"独立执行、不采信自报"这条原则是有必要的）：`test_ac_2_gold_at_threshold_boundary_no_coupon` 里，验收表原文只给了 `membershipDiscount=100`，这份测试自己额外推断并断言了 `discount == 100` 和 `finalAmount == 900`——推断本身是对的（金额1000，会员优惠100，无券，900正确），实测也确实通过，但如果它当时推错了数，从"6/6全过"这个统计里是会被我们的独立执行抓出来的，不会被它自己的回复文字掩盖。
- `test_vip100_no_stack_still_applies_when_no_membership_discount` 和其它几份一样，独立推出了"会员条件不满足时两种券都单独生效"这条结论。
- 用 `@pytest.mark.parametrize` 测了 6 种非法 `customerLevel`（含 `123`、`None` 这种类型错误而非仅字符串枚举错误，六份里覆盖类型层面最广的一份）。
- 没有发现读实现源码的痕迹；`decisionTrace` 只做类型检查。

## 结论
组合场景断言：**命中**。
