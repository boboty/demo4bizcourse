你是独立收到这个任务的，之前没有见过这个任务、这份文档，也没有任何相关背景。

## 任务

请基于下面提供的《需求》和《验收用例》文档，为一个 HTTP 接口编写一套 pytest 自动化测试。

## 背景与限制

- 待测接口是一个已经部署好、正在本地运行的 HTTP 服务：`http://127.0.0.1:8811`
- 你可以用 curl / httpx / requests 直接向这个地址发请求、观察真实响应，用来辅助设计测试断言。
- 你不需要、也不应该查看这个服务的实现源码。请把它当作一个黑盒接口来测试：不要用 Read / Glob / Grep / Bash(`find`/`cat`/`ls` 等) 去探索这个代码仓库里除了本提示词直接给你的内容之外的任何文件，尤其不要读取或搜索 `app/`、`business/`、`tests/`、`skills/`、`docs/`、`evidence/` 目录下的任何东西，也不要读取仓库里名字包含 acceptance、requirement、task、AC- 的其它文件。
- 除了本提示词提供的信息，不要假设你知道任何其他背景（例如不要假设这是某门课程的演示、不要假设某条规则特别容易出错）。

## 需求文档

```markdown
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

接口返回以下字段（完整类型定义见下方 openapi.yaml）：

- `eligible`：是否产生优惠
- `discount`：优惠总额
- `finalAmount`：优惠后的最终金额
- `membershipDiscount`：会员优惠金额
- `couponDiscount`：优惠券优惠金额
- `discountSources`：本次优惠的来源列表
- `reason`：优惠原因
- `decisionTrace`：本次计算经过的处理步骤记录
```

## 验收用例文档

```markdown
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
```

## OpenAPI 契约

```yaml
openapi: 3.1.0
info:
  title: AI Test Loop - Discount Preview
  version: 1.0.0
paths:
  /api/orders/discount-preview:
    post:
      summary: Preview order discount eligibility
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/DiscountPreviewRequest'
      responses:
        '200':
          description: Deterministic discount preview with decision evidence
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/DiscountPreviewResponse'
components:
  schemas:
    DiscountPreviewRequest:
      type: object
      required: [customerLevel, amount]
      properties:
        customerLevel: {type: string, enum: [GOLD, SILVER, STANDARD]}
        amount: {type: integer, minimum: 0}
        coupon: {type: [string, 'null'], enum: [VIP100, VIP100-NO-STACK, null]}
    DiscountPreviewResponse:
      type: object
      required: [eligible, discount, finalAmount, membershipDiscount, couponDiscount, discountSources, reason, decisionTrace]
      properties:
        eligible: {type: boolean}
        discount: {type: integer}
        finalAmount: {type: integer}
        membershipDiscount: {type: integer}
        couponDiscount: {type: integer}
        discountSources: {type: array, items: {type: string}}
        reason: {type: string}
        decisionTrace: {type: array, items: {type: string}}
```

## 交付

把最终的 pytest 测试文件完整写到这个绝对路径：`<project-root>/experiments/real-generation/trial-3/generated_test_orders.py`

测试文件里可以用 httpx 或 requests 向 `http://127.0.0.1:8811` 发请求（二选一即可；若用 httpx 用同步 Client 即可，不需要 async）。

写完之后，不需要你自己运行 pytest、也不需要验证测试是否通过——我们会独立执行并记录结果，不采用你自己的执行结论。

最后一步，请把你写的测试文件的完整最终代码，原样贴在你的最终回复正文里（作为回复的全部内容），不需要额外解释你的设计思路，不需要总结。
