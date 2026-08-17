# 人工评审：trial-2

## 独立执行结果
`python -m pytest experiments/real-generation/trial-2/generated_test_orders.py -v` → **36 passed, 0 failed**。

## 关键判定

**命中。** `test_ac5_gold_amount_1200_with_vip100_stacks` 同一函数内：
```python
assert body["membershipDiscount"] == 100
assert body["couponDiscount"] == 100
assert body["discount"] == 200
assert body["finalAmount"] == 1000
```
并且在文件末尾还有一个独立的 `test_discount_matrix`（`@pytest.mark.parametrize`，6组输入包含组合场景那一组）对 `discount`/`finalAmount` 做二次交叉验证——这组 parametrize 只验证聚合数字，单独看不够，但因为前面 `test_ac5` 已经把拆分断言做了，两者合起来是完整证据链，不是唯一依据。

## 其它观察

- 额外测了 `test_vip100_applies_alone_when_membership_not_eligible`（GOLD 但金额不到门槛时券单独生效）——这不是验收表给的场景，是从需求文字里自己推出来的边界组合。
- 有 `test_discount_equals_sum_of_membership_and_coupon_discount` 这种显式不变量测试。
- 输入校验覆盖较广：大小写敏感性（`gold` vs `GOLD`）、非整数金额、缺字段、非法券值都测了。
- 没有出现只有读源码才可能知道的内部实现细节；`decisionTrace`/`discountSources` 只做了存在性和类型检查。

## 结论
组合场景断言：**命中**，且有额外的交叉验证。
