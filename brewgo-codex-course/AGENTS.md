# BrewGo Workspace Guide

BrewGo 是面向美国 Amazon 市场的虚拟跨境电商品牌，核心产品是 G2 Portable Coffee Grinder。此仓库用于课程实验，不用于真实经营决策。

- 先读 `business/`，再处理业务数据；SKU 是跨表关联的主键。
- `business/`、`data/raw/` 和 `data/expected/` 是来自 Agent-demo-data 的课堂快照，不是 Source of Truth；不得覆盖、删除或原地修改。
- 课堂工作文件以 `data/work/` 为准；分析结果只写入 `outputs/<任务名>/`。
- 不确定或资料缺失的内容须清楚标注，不能补造产品、市场或客户事实。
- 价格、退款、Listing 修改、客户承诺、广告否定词和采购动作属于高风险事项，仅输出建议并要求人工确认。
- 处理数据时保留原字段，并以新增字段表达清洗、分类、判断和依据。
- 完成前检查文件范围、关键 SKU 引用、金额口径及输出是否可追溯。
