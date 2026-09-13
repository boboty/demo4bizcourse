# D0｜连续执行

第一讲只回答一个问题：

> Agent 已经不只是生成代码，它能不能在真实反馈下连续工作？

课堂要看见的链路：

```text
Run → FAIL → Read/Search → Observe → Edit → Run → PASS
```

D0 只证明这一件事。工程环境（Plan、项目记忆、代码规范、自检）是第二讲 D1 的内容；Golden Case 与独立验证是第三讲；规则沉淀是第四讲。D0 不碰这些。

## 课前准备

在 `ai-rd-system-demo/` 根目录执行：

```bash
source .venv/bin/activate
.venv/bin/python scripts/acceptance_check.py     # 全仓库，含 D1–D4
.venv/bin/python scripts/d0_verify.py            # 只含 D0
```

正常结果：两份都以 `OVERALL: PASS` 结束。再确认 Agent CLI 已登录（与 D1 相同环境）：

```bash
codex --version      # D0 课堂默认且已验证的 Agent
claude --version     # 备选：改用交互会话，见"兜底"一节
```

不需要额外 API key、endpoint 或模型变量。默认单次 watchdog 上限 600 秒；课前彩排可用 `D0_TIMEOUT_SECONDS=180` 缩短，这不是课堂变量。

## D0 起点是什么

```bash
./scripts/reset_d0.sh
cd workspaces/d0-first-loop
../../.venv/bin/python -m pytest -q
```

预期结果（这是 D0 的固定起点，不是临时制造的状态）：

```text
4 failed, 4 passed
```

- `tests/test_financing_baseline.py`：2 项通过。已有融资申请列表功能正常，**原有测试没有被破坏**。
- `tests/test_repayment_schedule.py`：2 项通过、4 项失败。同事把"放款后生成还款计划"做到一半：均摊舍入吃掉 0.01 尾差，且没有校验非法期数。

失败原因对研发人员一眼可读：

```text
assert 99999.99 == 100000.0          # 均摊后合计少了 0.01
Failed: DID NOT RAISE <class 'ValueError'>   # periods<=0 没有校验
```

这不是预制文字，也不是隐藏机关：测试、实现和数据都在 workspace 里，Agent 能读到同样的东西。

## 课堂运行流程

### 1. Reset

```bash
cd ai-rd-system-demo
./scripts/reset_d0.sh
```

### 2. 从 workspace 启动 Agent

课堂不要从仓库根目录启动会话。让学员看到起点：

```bash
cd workspaces/d0-first-loop
../../.venv/bin/python -m pytest -q      # 现场确认红灯（一秒内出结果）
```

然后在该目录启动已登录的 Agent（Codex 或 Claude Code 均可）。

一条命令跑完整链路并保存证据（讲师侧，等价于手动操作）：

```bash
cd ../..
./scripts/d0_run.sh
```

`d0_run.sh` 会先 reset，再以 workspace-write 权限启动 Agent，并把 `prompt.md`、`trace.jsonl`、`final.md`、`workspace.diff`、`result.json` 写进 `instructor/d0/results/latest/`。

### 3. 给 Agent 的现场任务文本

从 `instructor/d0/task.txt` 直接复制（课堂只念一次，念完不要再补充提示）：

```text
同事把“放款后生成还款计划”这个需求做到一半就休假了。接口和测试他已经先写好了，但测试还没跑通。

请你接手完成：

1. 先运行一遍测试，确认现在的状态；
2. 根据失败信息定位问题并修复，让全部测试通过；
3. 不要修改或删除测试来让它变绿；
4. 只改完成这个需求所必需的代码，不要做与本任务无关的重构。
```

任务文本只要求"先跑测试确认状态"，没有写失败原因，也没有写修法。

### 4. 课堂应该观察什么

| 节点 | 屏幕上应该出现 | 讲师要讲的一句话 |
| --- | --- | --- |
| Run | `../../.venv/bin/python -m pytest -q` | 它没有先改代码，而是先运行验证 |
| FAIL | `4 failed, 4 passed` | 失败来自这个项目真实存在的测试 |
| Read / Search | `rg`、`sed` 打开 `app/repayment/service.py` 和测试文件 | 它在读项目和测试，而不是凭感觉改 |
| Observe | Agent 说出"尾差"或"缺少校验" | 关键节点：反馈进入了它的下一步决策 |
| Edit | 只改 `app/repayment/service.py` | 改动落在待完成的模块，测试文件没被动 |
| Run | 再一次 `../../.venv/bin/python -m pytest -q` | 它自己复跑了 |
| PASS | `8 passed` | 修复完成，且原有融资列表测试仍绿 |

中途最容易讲透的一刻是 **Observe**：让学员看 Agent 的中间输出，确认下一步动作直接来自上一步的失败信息，而不是来自任何课堂提示。

### 5. 成功时应该看到什么

```bash
cd workspaces/d0-first-loop
../../.venv/bin/python -m pytest -q     # 8 passed
cd ../..
.venv/bin/python scripts/d0_verify.py   # OVERALL: PASS（它会先 reset，不影响课堂录像）
```

`instructor/d0/results/latest/result.json` 里的 `loop` 字段会给出机器可读的全部事实：

```json
{
  "actions": ["Run(FAIL)", "Read/Search", "Edit", "Run(PASS)"],
  "observed_failure_before_edit": true,
  "green_test_run_after_edit": true,
  "read_or_search_before_edit": true,
  "edited": true
}
```

`tests_modified` 必须为 `false`：Agent 是通过修实现变绿的，不是改测试。

## 兜底

### Agent 超时或跑偏

```bash
# 1. 让学员看真实的一次成功运行（同一个 baseline、同一个任务）
cat instructor/d0/fallback/final.md
cat instructor/d0/fallback/workspace.diff
cat instructor/d0/fallback/result.json

# 2. 直接恢复到修复后的目标状态，继续讲收口
./scripts/d0_restore_fixed.sh

# 3. 回到起点再演一次
./scripts/reset_d0.sh
```

`instructor/d0/fallback/` 保存的是**同一个 D0 baseline、同一个任务文本、同一种运行方式**下真实跑通的一次完整运行（trace、diff、最终说明、测试结果），不是另一个项目的录像。录屏说明见 `instructor/RECORDING-PLAN.md`。

### 现场只有 Claude Code 已登录

已实测：`claude -p`（`--permission-mode acceptEdits`）能正确读代码、改代码，但**跑不了 pytest**——无人值守模式下 Bash 需要逐次授权，Agent 会报告"命令被权限拦下"并跳过验证。那正好破坏 D0 唯一要证明的东西，所以不要用 `-p` 模式跑 D0。

正确做法是交互会话：

```bash
cd workspaces/d0-first-loop
claude          # 正常启动，逐次确认 Bash 与编辑
```

然后把 `instructor/d0/task.txt` 的文本粘进去，其余观察点与兜底完全一致。`D0_AGENT=claude` 只保留给 `--print` 模式的非课堂场景，不作为课堂路径。

## Checkpoint

D0 只有三个固定状态，不做多阶段状态机：

| Checkpoint | 命令 | 状态 |
| --- | --- | --- |
| `baseline` | `./scripts/reset_d0.sh` | 4 failed, 4 passed —— 课堂正式起点 |
| `failed` | 起点直接跑测试即可 | 与 baseline 相同；失败是起点自带的，不需要额外造 |
| `fixed` | `./scripts/d0_restore_fixed.sh` | 8 passed —— 兜底展示用的目标状态 |

`d0_restore_fixed.sh` 使用讲师侧参考实现 `instructor/reference/d0_repayment_service.py`，只用于兜底和验收，永远不进入课堂 workspace。

## 与 D1 的边界

D0 结束在"Agent 能在反馈下连续工作"，不回答"为什么它能稳定工作"。

收口的问题只有一个：

> 它刚刚自己读完了失败信息，自己决定改哪里。那——如果项目更大、任务更长、一次做不完，它还能这样连续工作吗？

第二讲 D1 从这个问题开始。
