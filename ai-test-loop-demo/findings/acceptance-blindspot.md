# 验收标准盲区：422 契约测试在 verified 里消失，没有任何机制报警

## 怎么注意到的

阶段一逐条对比 `tests/generated/test_orders.py` 与 `tests/verified/test_orders.py` 时发现：generated 里有 `test_invalid_customer_level_is_rejected_by_the_contract`（断言 `customerLevel=PLATINUM` 时返回 422），verified 里没有任何一条测试覆盖非法 `customerLevel` 或任何形式的输入校验。这条差异不是靠读 `run_independent_review.py` 的输出发现的——它对 generated 判 REJECTED、对 verified 判 PASS，全程没有提过这件事。是逐条对比两份测试文件的用例清单时人工看出来的。

## verified 删掉了什么

```python
def test_invalid_customer_level_is_rejected_by_the_contract() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/orders/discount-preview",
            json={"customerLevel": "PLATINUM", "amount": 1200, "coupon": "VIP100"},
        )
    assert response.status_code == 422
```

这是 generated 四条测试里唯一一条纯契约校验测试，不涉及优惠规则计算。verified 的四条测试（`test_gold_vip100_stacks_only_after_gold_is_evaluated`、`test_gold_discount_is_retained_when_coupon_cannot_stack`、`test_gold_threshold_and_no_discount_boundaries`、`test_vip100_coupon_evidence_is_explicit`）全部是业务规则测试，422 校验这条整个不见了，没有被替换、没有被合并进别的测试。

## `business/acceptance.md` 为什么没覆盖

`business/acceptance.md` 定义了 AC-001 到 AC-005，五条全部是优惠计算相关的业务规则（会员优惠金额、券优惠金额、叠加规则、金额与状态字段）。没有任何一条 AC 描述"非法输入应被拒绝"这件事。`api/openapi.yaml` 里 `customerLevel` 的 `enum: [GOLD, SILVER, STANDARD]` 约束是存在的（契约层面天然会让 `PLATINUM` 走 422），但这条约束从未被提升成一条独立的、需要测试证据的验收标准。也就是说，422 行为是接口契约（OpenAPI schema）保证的，但不是验收标准（acceptance.md）要求的——这是两个不同的文档，覆盖范围不重合。

## `run_independent_review.py` 为什么不会报警

`scripts/run_independent_review.py` 的 `review()` 函数只做一件事：拿 `business/acceptance.md` 里出现的 `AC-\d{3}` 编号，逐条检查测试源码里有没有声明覆盖（`covers:` 注释）+ 对应的关键断言字符串是否存在。它的检查范围严格等于 acceptance.md 里已经列出的 AC 条目集合（AC-001 到 AC-005）。由于 acceptance.md 里根本没有一条 AC 对应 422/输入校验，这个脚本的检查逻辑里也就没有任何一步会去找"是否存在输入校验测试"——不是它漏检了，是它的检查范围从设计上就不包含这件事，找不到就不会报，因为它压根不知道要找。

## 这类盲区的一般形态

验收脚本的判定范围继承自验收文档列出的条目集合；验收文档之外、契约文档（OpenAPI/schema）里单独存在的约束，不会被验收脚本自动纳入检查范围，即便测试代码在两个版本之间悄悄把这部分覆盖丢掉了，也不会触发任何一层现有机制的报警。
