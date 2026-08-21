# 需求：订单优惠预览接口

`POST /api/orders/discount-preview` 根据会员等级、订单金额与可选优惠券，计算订单可获得的优惠，并返回优惠明细供前端展示。金额单位为整数元，计算结果需保证确定性（相同输入永远得到相同输出）。

## 输入

- `customerLevel`：`GOLD` / `SILVER` / `STANDARD`
- `amount`：订单金额（整数元，不小于 0）
- `coupon`（可选）：`VIP100` / `VIP100-NO-STACK` / 不传

## 会员优惠规则

- 当 `customerLevel = GOLD` 且 `amount >= 1000` 时，享受会员优惠 100 元。
- 不满足以上条件时，会员优惠为 0 元。

## 优惠券规则

- `VIP100`：优惠 100 元。当订单同时满足会员优惠条件时，`VIP100` 与会员优惠共同生效，此时优惠总额为两者之和（200 元）。
- `VIP100-NO-STACK`：优惠 100 元。当订单同时满足会员优惠条件时，`VIP100-NO-STACK` 不与会员优惠共同生效——订单仍保留会员优惠（100 元），优惠券本身不再额外增加优惠金额。
- 未使用优惠券时，优惠券部分不产生优惠。
- 非法的 `customerLevel` 取值应被接口拒绝。

## 响应字段

接口返回以下字段（完整类型定义见 `openapi.yaml`）：

- `eligible`：是否产生优惠
- `discount`：优惠总额
- `finalAmount`：优惠后的最终金额
- `membershipDiscount`：会员优惠金额
- `couponDiscount`：优惠券优惠金额
- `discountSources`：本次优惠的来源列表
- `reason`：优惠原因
- `decisionTrace`：本次计算经过的处理步骤记录
