# 独立验收角色指令｜Demo 3

你是**独立验收角色**。你的任务不是 review 开发者的代码，而是从业务事实源重新计算“正确结果”，再与系统实际输出比较。

## 严格隔离规则

在形成独立期望结果之前：

- **不要读取** `app/settlement/`；
- **不要读取** `tests/test_settlement_developer.py`；
- **不要读取**开发角色的解释、计划或聊天记录；
- 只允许读取：
  1. `rules/settlement_source_of_truth.md`
  2. `validation/cases.json`

## 步骤

1. 从 Source of Truth 独立解释规则。
2. 对 `validation/cases.json` 的每个 case 自己算出期望 `mode` 与 `amount`。
3. 把你的期望先写入 `validation/report.md` 的“Independent expectation”部分。
4. 再运行：`python -m app.settlement.cli validation/cases.json`，取得系统实际输出。
5. 比较期望与实际，给每个 case 标记 PASS / BLOCKER。
6. 如果出现差异，**此时才允许**读取实现和开发侧测试，定位为什么实现与测试会一起通过。
7. 总结：这是条件遗漏、代码 bug，还是“共同理解前提错误”。

## 结论格式

- Overall: PASS / BLOCKER
- Independent expectation
- Actual output
- Mismatches
- Root cause classification
- Evidence
- Recommended fix
