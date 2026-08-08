# BrewGo Codex 课堂 Demo

这是《跨境电商 Codex 实战：从 AI 助手到业务智能体》的独立课堂运行项目。BrewGo 面向美国 Amazon 市场销售虚构产品 **G2 Portable Coffee Grinder**；所有客户、订单和经营数据均为教学用途。

本项目中的 `business/`、`data/raw/` 和 `data/expected/` 是课堂本地快照，权威 Source of Truth 位于 `Agent-demo-data/cross-border-ecommerce/brewgo/`。课堂授课时不依赖该外部项目存在。

## 3 分钟起步

1. 在 `business/` 阅读业务背景、产品事实、品牌与业务规则。
2. 在 `data/raw/` 查看只读原始数据；在 `data/work/` 操作课堂副本；`data/expected/` 保存 reset 基线。
3. 在 `tasks/` 选择本节课任务，分析结果保存至 `outputs/<任务名>/`。
4. 演示结束运行 `python3 scripts/reset_demo.py` 恢复工作文件并清空输出。

## 目录说明

- `reference/`：课程上下文与课堂使用方式。
- `business/`：BrewGo 业务事实、字段字典和约束的课堂快照。
- `data/raw/`：不可修改的课堂数据快照。
- `data/work/`：课堂可编辑的工作副本。
- `data/expected/`：只读恢复基线，reset 会从这里恢复 `data/work/`。
- `tasks/`：按岗位组织的任务说明。
- `outputs/`：课堂分析结果，只能在这里新增文件。
- `data/brewgo_data_manifest.json`：快照版本和 SHA-256 清单。

## 数据约束

不要修改 `data/raw/`；不确定信息必须标注为“推测/待确认”。价格、退款、Listing 发布、客户承诺和采购下单只能给出建议，必须人工确认。

`orders.xlsx` 是订单异常分析用的非代表性样本，不是店铺全量订单；`inventory.xlsx` 的平均日销是独立运营口径，Amazon Ads 是聚合归因口径。三者不得直接做总量对账或逐单归因。

## Reset

在项目根目录运行：

```bash
python3 scripts/reset_demo.py
```

Reset 只清空 `outputs/`（保留 `.gitkeep`）并用本地 `data/expected/` 恢复 `data/work/`，不会修改 `data/raw/`。

## 开发期数据同步

数据维护者在 `Agent-demo-data/cross-border-ecommerce/brewgo/` 运行 `python3 scripts/sync_brewgo_data.py`。默认同步快照且不动 work；只有显式 `--reset` 才恢复 work。同步不会覆盖本项目的 `outputs/`、Task、AGENTS 或其他课堂资产。

## 后续课堂

本轮只完成数据验收、项目分离和同步治理。FBA Calculator、Listing Checker、Ads Cleaner、Skill、Automation 和 Multi-Agent 均未实现。
