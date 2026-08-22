# 讲师 Runbook｜4 讲 4 Demo

## 总原则

同一个 Git 仓库只用于保存资产；Codex 的 workspace 必须是下面五个目录之一。每次切换 Demo 都先执行对应 reset，再从目标目录新开 Codex。不要从 `ai-rd-system-demo/` 根目录启动课堂会话。

所有命令默认从 `ai-rd-system-demo/` 根目录执行；每个代码块中的 `cd` 都是课堂操作的一部分。

## Demo 1｜demo1-vague｜一句话需求｜15 min

### 1A. CNN 可视化｜约 5 min

打开 Adam Harley CNN 3D 可视化：<https://adamharley.com/nn_vis/cnn/3d.html>。

收口：模型内部面对的往往不是一个答案，而是一组候选；业务系统最终必须落成一个判断。

### 1B. 从独立 workspace 启动 Codex｜约 10 min

```bash
./scripts/reset_demo1.sh
cd workspaces/demo1-vague
```

从这个目录新开 Codex 会话，然后只粘贴下面这一句话：

> 给融资申请列表增加客户名称和融资状态筛选，并支持导出。

不补充信息，观察它是直接做还是追问；如果有改动，只展示 diff、追问和完成依据，不修复、不运行后续 Demo 的材料。

如需保存现场差异，回到仓库根目录执行：

```bash
cd ../..
./scripts/capture_diff.sh demo1
```

## Demo 2｜demo2-five-elements｜五要素任务｜15 min + 学员 25 min

Demo 1 会话结束后，必须切换目录并新开会话：

```bash
./scripts/reset_demo2.sh
cd workspaces/demo2-five-elements
```

在新会话中读取并粘贴 `task-a-five-elements.md` 的完整内容。五要素里的业务边界、约束、交付物和验收标准以该文件为准，不改写其业务内容。

允许 Codex 修改。开发 Agent 只运行开发侧测试，不读取或运行讲师 workspace 外的独立验收脚本；会话结束后退出 Demo 2 workspace，再由讲师执行隐藏验收：

```bash
pytest -q
cd ../..
python3 instructor/checks/task_a_acceptance.py
./scripts/capture_diff.sh demo2
```

`python3 instructor/checks/task_a_acceptance.py` 只能由讲师在 workspace 外运行。独立验收脚本只存在于 `instructor/`，不会出现在 Demo 2 workspace。落点：五要素的价值不是让 Prompt 更长，而是让“完成”第一次有了共同定义。

## Demo 3｜两个独立上下文｜45 min

### 3A. developer｜历史错误但开发测试全绿

```bash
./scripts/restore_demo3_wrong.sh
cd workspaces/demo3-developer
```

从这个目录新开 developer Codex 会话，读取 `tasks/task-b-development.md`，展示当前实现和开发侧测试：

```bash
pytest -q tests/test_settlement_developer.py
```

这里保持“汇损 + 退税双候选”的错误状态：实现和开发测试同源，全绿不是业务正确性的证明。测试全绿后，在 developer workspace 的另一个终端启动固定端口黑盒服务，并保持该终端运行：

```bash
./bin/start-blackbox
# 服务保持在 http://127.0.0.1:8765
```

### 3B. validator｜切换 workspace 后新开独立验收会话

关闭或暂停 developer 会话，切换到另一个 workspace，再新开 validator Codex 会话：

```bash
cd ../demo3-validator
```

在黑盒服务保持运行时，从 validator workspace 新开 Codex 会话，粘贴 `instructor/prompts/demo3/03-validation.md`，并强调：形成 Independent Expectation 之前，只能读 validator workspace 中的 Source of Truth 与 Golden Case 输入，不能读取 developer workspace 的实现、开发测试或聊天记录。实际结果只能通过 HTTP 黑盒入口获取：

```bash
bin/actual-output validation/cases.json
```

错误态必须稳定得到：

```text
GC-01 expected = 6200 / FX_LOSS_PLUS_TAX_REFUND
GC-01 actual = 5000 / TAX_REFUND_ONLY
Overall = BLOCKER
```

此后由讲师在 developer workspace 展示共同理解偏差并让 Code 修复；不要为了剧情伪造模型失败。修复态兜底：

```bash
cd ../..
./scripts/restore_demo3_fixed.sh
cd workspaces/demo3-validator
bin/actual-output validation/cases.json
```

修复后 validator 应为 `Overall = PASS`。`restore_demo3_fixed.sh` 只恢复 developer 的正确实现与测试；validator 始终通过黑盒入口取结果。

## Demo 4｜demo4-sedimentation｜同 workspace，新会话｜15 min

从 Demo 3 正确修复状态开始，使用独立的 Demo 4 workspace：

```bash
./scripts/reset_demo4.sh
cd workspaces/demo4-sedimentation
```

在这里新开第一个 Codex 会话，粘贴 `instructor/prompts/demo4/04-retro.md`。让复盘角色读取 `reports/demo3-validation.md`，把可复用规则写入：

- `AGENTS.md`
- `validation/checklist.md`

初始 `AGENTS.md` 不含“双候选优先”规则；复盘后必须出现“组合候选先评估，只有被明确排除才回退到退税单候选”的规则。展示 diff 后，关闭旧 Codex 会话。

重点：仍在同一个 `demo4-sedimentation` workspace，但必须新开一个全新 Codex 会话：

```bash
# 仍在 workspaces/demo4-sedimentation，不要 cd 到别处
```

新会话只粘贴 `tasks/task-b-variant.md` 并让它依赖会话启动时加载的项目级规则，不读取 `rules/`、`validation/`、`app/`、`tests/`，也不依赖历史聊天。预期：`FX_LOSS_PLUS_TAX_REFUND`，金额 `11,000`。

如果复盘现场需要确定性兜底：

```bash
cd ../..
./scripts/restore_demo4_learned.sh
```

## Reset / restore 对照

| 场景 | 起始状态 | 命令 |
| --- | --- | --- |
| Demo 1 | 融资申请 baseline | `./scripts/reset_demo1.sh` |
| Demo 2 | 相同 baseline + 五要素任务包 | `./scripts/reset_demo2.sh` |
| Demo 2 兜底 | 参考实现 | `./scripts/restore_demo2_reference.sh` |
| Demo 3 developer + validator | 错误实现、开发测试全绿 | `./scripts/restore_demo3_wrong.sh` |
| Demo 3 developer | 正确修复态 | `./scripts/restore_demo3_fixed.sh` |
| Demo 4 | 正确修复项目、未沉淀规则 | `./scripts/reset_demo4.sh` |
| Demo 4 兜底 | 已沉淀规则 | `./scripts/restore_demo4_learned.sh` |

本轮结构验收：

```bash
python3 scripts/acceptance_check.py
```

该命令只做自动检查，不启动真实课堂流程，也不让 Codex 执行任务 A/B。
