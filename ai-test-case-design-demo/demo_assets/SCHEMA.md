# 业务资产与 JSON 契约

所有 JSON 使用 UTF-8、稳定 ID；钱以两位小数字符串表示，避免二进制浮点误差。引用字段存 ID 数组，校验器应检查所有引用存在。

- `prd/`：最小版本需求；段落 ID 是需求来源。V1.1 的 `changes` 仅列三项获准变化。
- `business/analysis.json`：角色、输入、流程、状态、规则、外部依赖、风险和待确认项；条目标 `fact`、`inference`、`missing` 或 `conflict`，并附来源/风险/决策状态。
- `business/rules.json`：可追溯规则目录。每条给来源、证据等级、适用范围和待确认状态。
- `finance/after_sales_funds.json`：独立规范，课堂在 Demo 4 揭示。不能被 Demo 2 的 V1.0 冻结输入引用。
- `scenarios/candidates.json`：候选场景；每个场景包含分类、规则引用、角色输入/状态条件、风险影响/概率/难发现性及执行成本。理论维度与无效组合另列。
- `cases/v1_0_executable.json`：20 条独立可执行的输入/预期，显式标记采用的假设口径；执行结果须由后续逻辑计算，禁止静态 PASS。
- `frozen/`：一次 AI 输出及两轮 Review 的冻结课堂证物，每份标 `frozen: true`、输入来源及限制。
- `history/`：历史 V1.0 场景/用例和 V1.1 迁移依据。迁移只记录规则差异及显式判定规则，Phase 2 按引用关系推导保留/修改/作废/新增，不预置推导结果冒充分析。
- `practice/`：Demo 3 第二讲、Demo 6 第四讲的学员输入与讲师参考答案分目录隔离。

主要契约实体：规则 `rule_id`，场景 `scenario_id`，用例 `case_id`，需求来源 `source_id`；`rule_ids` / `scenario_ids` / `case_ids` 建立依赖图。状态只有在有明确证据时才允许由执行器产生。
