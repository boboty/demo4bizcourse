# 字段字典（V1）

SKU 是产品、广告、订单、库存和成本的主要连接键。使用前可新增 `normalized_sku`，但不得覆盖原值。金额默认按单件或表内行口径；凡币种、费率或时间范围不清楚时必须先确认。

| 数据集 | 字段 | 类型 / 单位 | 含义与注意事项 |
|---|---|---|---|
| products | `sku`, `asin` | 文本 | 商品与 Amazon 标识；SKU 含故意的空格/重复问题 |
| products | `product_name`, `variation`, `color` | 文本 | 产品、变体/套装与颜色 |
| products | `material`, `dimensions` | 文本 | 材质与尺寸原始描述，格式可能不统一 |
| products | `weight`, `unit` | 数值 + g/kg | 重量数值和单位必须联动换算 |
| products | `purchase_cost`, `selling_price` | USD / 件 | 主数据中的采购成本与标准售价 |
| products | `supplier`, `status` | 文本 | 主要供应商和商品状态 |
| search_terms | `date_range` | 文本日期区间 | 聚合观察期，格式故意混用 |
| search_terms | `campaign`, `ad_group`, `sku` | 文本 | 广告层级与归属 SKU |
| search_terms | `search_term`, `match_type` | 文本 | 用户搜索词与匹配类型 |
| search_terms | `impressions`, `clicks`, `orders` | 非负整数 | 展示、点击、Amazon Ads 归因订单 |
| search_terms | `spend`, `sales` | USD | 广告花费与归因销售额 |
| search_terms | `ctr`, `cvr`, `acos` | 公式百分比 | 点击/展示、订单/点击、花费/销售；销售为零时 ACoS 仅是计算表现，不代表可直接否定 |
| supplier_quotes | `supplier`, `scope` | 文本 | 供应商与报价范围；整机和组件不可直接比较 |
| supplier_quotes | `unit_price`, `currency` | 金额 + USD/CNY | 原币单价，换算时需保留原值 |
| supplier_quotes | `MOQ`, `lead_time_days` | 件、天 | 最小起订量与交期 |
| supplier_quotes | `payment_terms`, `packaging`, `inspection`, `shipping_terms`, `notes` | 文本 | 付款、包装、质检、贸易条款及其他约束 |
| reviews | `review_id`, `review_date`, `sku` | 文本、ISO 日期 | 评论标识、日期和关联 SKU |
| reviews | `rating`, `title`, `review_text` | 1–5、文本 | 星级和用户原文 |
| reviews | `verified_purchase`, `helpful_votes` | Y/N、整数 | 已验证购买标记和有用票数 |
| reviews | `topic_hint` | 文本 | 教学辅助标签，不是最终归因真相 |
| customer_service | `ticket_id`, `opened_date`, `order_id`, `sku` | 文本、ISO 日期 | 工单及关联标识；`order_id` 必须存在于订单样本，且工单 SKU 必须与该订单一致 |
| customer_service | `channel`, `customer_message`, `category` | 文本 | 渠道、客户原文和初始分类 |
| customer_service | `risk_level`, `agent_note` | Low–Critical、文本 | 风险提示与人工处理线索，不能替代审批 |
| orders | `order_id`, `order_date`, `sku` | 文本、ISO 日期 | 订单与商品标识 |
| orders | `quantity`, `unit_price`, `sales_total` | 件、USD | 数量、成交单价和公式销售额 |
| orders | `status`, `fulfillment`, `ship_days` | 文本、天 | 订单、履约方式与时效；缺失不等于零 |
| orders | `refund_amount`, `customer_region`, `note` | USD、文本 | 退款、美国区域与异常备注 |
| inventory | `current_stock`, `inbound`, `reserved` | 件 | 当前、在途与预留库存 |
| inventory | `avg_daily_sales`, `lead_time_days`, `safety_stock` | 件/天、天、件 | 日销、交期与安全库存 |
| inventory | `stock_cover_days`, `risk_status` | 公式数值、文本 | 覆盖天数与基础规则提示；业务结论仍需结合状态和备注 |
| cost_parameters | `selling_price`, `purchase_cost` | USD / 件 | 利润输入快照，可能与产品主表待确认 |
| cost_parameters | `inbound_freight`, `fba_fee`, `advertising_cost`, `other_cost` | USD / 件 | 入仓、履约、广告和其他成本 |
| cost_parameters | `amazon_fee_rate`, `return_rate` | 0–1 小数 | 销售佣金率与退货率 |
| cost_parameters | `exchange_rate` | CNY/USD 假设 | 课堂换算参数；不要对已经是 USD 的采购成本重复换算 |
| cost_parameters | `parameter_status`, `note` | 文本 | 参数完整性和口径说明 |
