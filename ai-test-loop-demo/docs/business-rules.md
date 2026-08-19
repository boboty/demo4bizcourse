# 业务规则：订单优惠计算（Source of Truth）

本文件是课堂测试 Agent 判断「接口结果是否正确」的唯一业务依据。所有断言以本文件为准。

## 接口

`POST /api/orders/calculate`

请求字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `amount` | integer | 订单金额，单位：元，必须 >= 0 |
| `memberLevel` | string | 会员等级：`GOLD` / `SILVER` / `STANDARD` |

返回字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `status` | string | 固定为 `SUCCESS` |
| `discount` | integer | 优惠金额，单位：元 |
| `finalAmount` | integer | 最终应付金额，单位：元 |

## 优惠规则

1. GOLD 会员：
   - `amount >= 1000` 时，`discount = 200`；
   - `amount < 1000` 时，`discount = 0`。
2. SILVER 会员：
   - `amount >= 1000` 时，`discount = 100`；
   - `amount < 1000` 时，`discount = 0`。
3. STANDARD（普通会员）：任何金额都不优惠，`discount = 0`。
4. 最终应付金额必须满足：`finalAmount = amount - discount`。

## 标准示例

| 请求 | discount | finalAmount |
| --- | --- | --- |
| `amount=1000, memberLevel=GOLD` | 200 | **800** |
| `amount=999, memberLevel=GOLD` | 0 | 999 |
| `amount=1001, memberLevel=GOLD` | 200 | 801 |
| `amount=1000, memberLevel=SILVER` | 100 | 900 |
| `amount=999, memberLevel=SILVER` | 0 | 999 |
| `amount=1000, memberLevel=STANDARD` | 0 | 1000 |

> 关键：接口返回 `status=SUCCESS`、HTTP 200 只代表请求被正常处理，
> 不代表业务计算正确。任何返回都必须再按上述规则核对 `discount` 与 `finalAmount`。
