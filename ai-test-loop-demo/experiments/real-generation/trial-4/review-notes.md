# 人工评审：trial-4

## 独立执行结果
`python -m pytest experiments/real-generation/trial-4/generated_test_orders.py -v` → **45 passed, 0 failed**（六次里测试数最多的一份）。

## 关键判定

**命中，而且是六份里覆盖最扎实的一份。** `test_case_5_gold_1200_vip100_stacks`：
```python
assert body["membershipDiscount"] == 100
assert body["couponDiscount"] == 100
assert body["discount"] == 200
assert body["finalAmount"] == 1000
```
更进一步，`TestCouponRules.test_stacking_behavior_when_membership_condition_met` 用 `@pytest.mark.parametrize("coupon,expected_coupon_discount", [("VIP100", 100), ("VIP100-NO-STACK", 0)])` 把"叠加"与"不叠加"两种券在会员条件满足时的行为写成一组对照参数化测试——这已经不是简单转录验收表了，是主动把"同一门槛条件下两种优惠券行为对比"设计成了测试结构本身。

## 其它观察

- `assert_contract_shape` 里连 `bool` 会被 Python 当成 `int` 子类这个坑都处理了（`isinstance(x, int) and not isinstance(x, bool)`），说明这份测试在类型校验上比其它几份更较真。
- 专门测了"GOLD 但金额不到门槛（500）时 VIP100 仍独立生效"，以及同样条件下 VIP100 在 SILVER 等级时的行为——把"会员条件"和"优惠券条件"当成两个独立变量做了正交测试，覆盖面在六份里最广。
- 用 `@pytest.mark.parametrize` 覆盖了 6 种非法 `customerLevel` 取值和 4 种非法 `coupon` 取值。
- 没有发现读实现源码的痕迹。

## 结论
组合场景断言：**命中**，覆盖深度六份中最高。
