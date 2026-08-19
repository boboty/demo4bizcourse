# 人工评审：trial-3

## 独立执行结果
`python -m pytest experiments/real-generation/trial-3/generated_test_orders.py -v` → **30 passed, 0 failed**（trial 自己在回复里也报了"30 passed"，与独立执行结果一致，但结论以独立执行为准，不是因为自报一致就采信）。

## 关键判定

**命中。** `test_case5_gold_1200_vip100_stacks_with_membership`：
```python
assert data["membershipDiscount"] == 100
assert data["couponDiscount"] == 100
assert data["discount"] == 200
assert data["finalAmount"] == 1000
```
经由 `assert_full_response` 辅助函数间接调用（该函数内部会先做 schema 校验和 `assert_business_invariants`，再返回 `data` 给调用方做具体断言）——多一层封装，但断言链条完整可追踪，不是把断言"藏"没了。

## 其它观察

- 额外加了一条其它几个 trial 都没有的不变量：`discountSources` 的元素个数应该等于"实际生效的优惠项个数"（`expected_source_count`），这是比"discount == 两者之和"更严格的交叉检查。
- `TestCouponRule` 里专门测了"会员条件不满足时，VIP100 与 VIP100-NO-STACK 应该行为一致（因为没有可叠加的对象）"——这条推理和 trial-1/2/4/5/6 独立地得出了同样的结论，说明这是从需求文字（"当订单同时满足会员优惠条件时……不叠加"）能直接推出的，不是巧合抄的。
- 输入校验里专门测了大小写敏感（`gold`/`Gold`/`GOLDEN`）。
- 没有发现读实现源码的痕迹。

## 结论
组合场景断言：**命中**。
