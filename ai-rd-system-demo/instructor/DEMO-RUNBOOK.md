# 讲师 Runbook｜4 讲 4 Demo

## Demo 1｜第一讲｜15 min

### 1A. CNN 可视化（约 5 min）
打开：https://adamharley.com/nn_vis/cnn/3d.html

目标：可视化“模型面对的是候选分布，业务系统最终却要落成一个判断”。

建议动作：现场写一个介于 4/9 或 1/7 之间的模糊数字；只看输出候选强弱，不讲 CNN 数学。

收口：**模型内部面对的往往不是一个答案，而是一组候选；但业务系统最终必须落成一个判断。**

### 1B. 一句话交给 Codex（约 10 min）
1. `./scripts/reset_base.sh`
2. 从仓库根目录打开一个新的 Codex 会话。
3. 粘贴 `tasks/task-a-vague.txt`。
4. 不补充信息，观察它是直接做还是追问。
5. 如果有改动：`./scripts/capture_diff.sh demo1`
6. 只展示 diff / 追问 / 完成依据，不修。

**鲁棒分支**：
- 它直接做：看它自行补了哪些假设。
- 它追问：说明任务没有达到可交办状态。
- 它做得很好：问“凭什么证明已经完成”。

落点：**刚才给的是一句需求，不是一个可验收的研发任务。**

---

## Demo 2｜第二讲｜15 min + 学员 25 min

1. `./scripts/reset_base.sh`
2. 新 Codex 会话，粘贴 `tasks/task-a-five-elements.md`。
3. 展示 5 行计划。
4. 允许 Codex 修改。
5. 展示 diff。
6. 跑 `pytest -q`。
7. 跑 `python instructor/checks/task_a_acceptance.py`。
8. `./scripts/capture_diff.sh demo2`
9. 并排对比 `instructor/captures/demo1.patch` 与 `demo2.patch`（若 Demo1 无 patch，就对比 Demo1 的追问 / 假设记录）。

落点：**五要素的价值不是让 Prompt 更长，而是让“完成”第一次有了共同定义。**

学员实战：5 分钟说明 + 12 分钟自己写 + 5 分钟互评 + 3 分钟公共收口。
公共问题：**“换给旁边的人以后，哪一项最容易被误解？”**

---

## Demo 3｜第三讲｜45 min

### 课前准备
`./scripts/reset_base.sh`。基线中的任务 B 是“历史错误运行”：实现与开发侧测试同源，全绿但业务错误。

讲师提示：任务 B 的“开发侧测试”**故意与错误理解同源**，所以全绿不是业务正确性的证明。

如果你希望前两个角色也现场跑，可用 `prompts/demo3/`；但高潮不依赖开发角色现场犯错。**绝不要为了剧情伪造模型失败。**

### ① 作战室角色（6 min）
展示：调度（control plane） / 沉思（需求设计） / Code（开发） / 验收（独立） / 复盘（先不打开）。
说明：调度不是第五种责任；复盘留到第四讲。

### ② 快速走到“开发完成”（6 min）
- 展示当前实现与开发侧测试。
- 跑：`pytest -q tests/test_settlement_developer.py`
- 屏幕上出现全绿。

### ③ 独立验收（约 28 min）
1. **停住问台下：到这里你会放行吗？**
2. 新开独立验收上下文，粘贴 `prompts/demo3/03-validation.md`。
3. 验收角色只能先读 Source of Truth + cases。
4. 它写独立期望，再运行黑盒输出。
5. 预期 GC-01 出现 BLOCKER：系统返回 5000 / TAX_REFUND_ONLY，独立期望为 6200 / FX_LOSS_PLUS_TAX_REFUND。
6. 此时再允许它读实现与开发测试，揭示“实现和测试共享了同一错误前提”。
7. 让 Code 修复。
8. 重新跑开发测试与独立验收。开发侧旧测试应暴露，需要同步修正为正确规则。

确定性兜底：
- 错误态：`./scripts/restore_demo3_wrong.sh`
- 修复态：`./scripts/restore_demo3_fixed.sh`
- 独立检查：`python validation/independent_check.py`

**兜底说明：**这个脚本只在真机独立验收路径失败时救场；它比对的是预先算好的对照结果，不是现场独立推导，使用时必须明确说明。能录屏时优先使用录屏证据。

### ④ 收口（5 min）
**救回这一次的，不是更多测试，而是第二个独立理解源。**

落回客户只说一句：**你们这边对应的就是额度口径、状态口径、资产认定口径这类规则。**

---

## Demo 4｜第四讲｜15 min

前提：Demo 3 已经修复，并产生验收报告。

1. 打开此前留白的“复盘”角色。
2. 粘贴 `prompts/demo4/04-retro.md`。
3. 让它把教训写进 `AGENTS.md` + `validation/checklist.md`。
4. 展示 diff：**不是写 case 复盘，而是写可复用规则。**
5. 关闭旧 Codex 会话。
6. 新开一个全新 Codex 会话（必须是新会话，因为 AGENTS.md 在会话启动时加载）。
7. 粘贴 `prompts/demo4/05-new-session.md`。
8. 它应按项目规则直接选 `FX_LOSS_PLUS_TAX_REFUND`，金额 11,000，并指出组合候选优先规则。

落点：**会话是新的，模型可以换，规则还在。模型的归模型，沉淀的归沉淀。**
