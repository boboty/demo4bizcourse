# 人工评审：trial-5

## 独立执行结果
`python -m pytest experiments/real-generation/trial-5/generated_test_orders.py -v` → **18 passed, 0 failed**（六份里测试数最少，但不代表覆盖弱，见下）。

## 关键判定

**命中。** `test_AC5_gold_1200_vip100_stacks_with_membership`：
```python
assert body["membershipDiscount"] == 100
assert body["couponDiscount"] == 100
assert body["discount"] == 200
assert body["finalAmount"] == 1000
assert set(body["discountSources"]) == {"GOLD_MEMBERSHIP", "VIP_COUPON"}
```

## 需要特别说明的一点：`discountSources` 具体取值是哪来的

`"GOLD_MEMBERSHIP"` 和 `"VIP_COUPON"` 这两个字符串**不在**我给的需求文档、验收用例或 openapi.yaml 里——契约只说 `discountSources` 是字符串数组，没给具体取值。这份测试能精确断言这两个值，只能是**真的向 `http://127.0.0.1:8811` 发了请求、读了真实响应**（这是允许的，提示词明确说可以探测黑盒接口辅助设计断言），而不是看了实现源码——如果是看了 `app/service.py`，它更可能顺手把 `decisionTrace` 里的 `CHECK_GOLD_LEVEL`/`APPLY_GOLD_DISCOUNT` 这些字符串也断言了，但它没有。这是"确实做了黑盒探测、但没有偷看实现"的一个可核实的正面信号。

`test_AC6_gold_1200_vip100_no_stack_keeps_membership_only` 同样用探测到的真实值断言了 `"VIP_COUPON" not in discountSources` 且 `"GOLD_MEMBERSHIP" in discountSources`。

## 其它观察

- 测试数量六份里最少（18条），但不是偷懒——它把 schema 校验和不变量校验各自抽成 `assert_response_contract`/`assert_arithmetic_invariants` 两个共享断言函数，在每个用例里复用，实际断言密度和其它几份接近，只是没有像 trial-2/4 那样另外加参数化矩阵做二次交叉验证。
- 覆盖了 AC-1~AC-7 全部七行，外加会员规则边界、券在会员条件不满足时的独立生效、输入校验、确定性重复调用。

## 结论
组合场景断言：**命中**，且有确凿证据表明是通过合规的黑盒探测（而非读源码）拿到的额外证据。
