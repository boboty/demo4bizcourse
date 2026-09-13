# D1｜工程现场接力：新会话如何找到自己的坐标

第二讲现在的主 demo 只回答一个问题：

> 一个完全新的 Agent Session，没有上一轮聊天记录，能不能仅凭工程现场重新找到——当前任务是什么、已经完成了什么、为什么这么做、下一步该做什么、工程是否健康，并把最新状态写回去？

课堂要落的一句话：

> **这个新 Session 没有上一轮聊天记录，但它仍然知道自己站在哪里。**

D1 只使用已经登录的 Codex / Plus 环境；模型和 provider 属于课前环境，不是本讲的比较变量。原来的 Task → Plan → 项目环境 → 自检要求 三级对比实验（Level 1/2/3）仍然保留，作为**补充实验**放在本文件末尾，课堂时间紧张时可以整段跳过。

课堂统一使用总入口 [DEMO-RUNBOOK.html](DEMO-RUNBOOK.html)（导航：D0 连续执行 → D1 Fresh Session → 既有 Demo），其中的 D1 Fresh Session 小节就是本文件"课堂运行流程"一节的可点击/可复制版本。`D1-HANDOFF-RUNBOOK.html` 仍保留在仓库里，但只作为开发/调试参考，不再作为课堂独立入口。

## 课前准备

在 `ai-rd-system-demo/` 根目录执行：

```bash
source .venv/bin/activate
./scripts/d1_handoff_verify_setup.py
```

只需确认 Codex 已登录并可运行 `codex exec`；不需要设置额外 API key、endpoint、模型或 provider 变量。默认单次 watchdog 上限为 300 秒，课前彩排可临时设置 `D1_HANDOFF_TIMEOUT_SECONDS=120`，这不是课堂变量。

## 工程现场设计

同一个融资申请最小工程（`instructor/baselines/d1-financing-minimal` 的任务）：

> 给融资申请列表增加客户名称和融资状态筛选，并支持导出。

固定的"中途接手"起点由 `workspaces/d1-handoff/` 提供，每次 `./scripts/reset_d1_handoff.sh` 都会重放同样的三次提交：

1. `chore: start financing filter+export task (baseline + TASK/PROGRESS/DECISIONS scaffolding)` —— 任务刚开始，脚手架文件都在，功能还没做。
2. `feat(financing): add customer_name filter; log decision D-001/D-002/D-003 and handoff state` —— **已经完成客户名称筛选**并有测试，同时在 `DECISIONS.md` 记了三条工程决策。
3. `chore: session ended — see PROGRESS.md for next step` —— 空提交，显式标记"上一个 session 到这里结束"。

workspace 里可用的工程现场资产：

| 文件 | 作用 |
| --- | --- |
| `TASK.md` | 原始任务 + 开发侧验收方向 |
| `PROGRESS.md` | 当前做到哪里：已完成客户名称筛选，未完成状态筛选和导出 |
| `DECISIONS.md` | 为什么这么做：筛选顺序（权限→筛选→分页）、模糊匹配语义、类型注解写法 |
| `feature-list.json` | 机器可读的功能级完成情况 |
| `verify.sh` | 健康检查：跑现有 pytest，优先用仓库共享 `.venv`，找不到才退回系统 `python3` |
| `PROJECT-MEMORY.md` / `CODING-STANDARDS.md` | 长期项目事实和规范，不随任务进度变化 |
| `AGENTS.md` | workspace 隔离规则 + 指路（"这里没有历史聊天记录，请从这些文件重新建立坐标"） |
| Git History | 三次提交，最后一条显式标记 session 已结束 |

`PROGRESS.md`/`DECISIONS.md`/`feature-list.json` 是"当前任务状态"，会随每次 session 结束更新；`PROJECT-MEMORY.md`/`CODING-STANDARDS.md` 是"项目长期事实"，只在架构真正变化时更新——这个区分本身就是课堂要讲的内容。

D1 只用到开发侧 `verify.sh`（本质是 `pytest`），不使用 Golden Case、独立 Validator 或外部 Source of Truth——那是第三讲的内容；也不引入 Skill、规则生命周期或防复发资产——那是第四讲的内容。

## 课堂运行流程

### 0. 讲师先做五个预测

在启动全新 session 之前，让学员或讲师自己先看一眼工程现场（`cat` 这几份文件即可），预测新 session 会不会命中：

1. 识别当前任务（客户名称+状态筛选+导出）；
2. 识别已完成项（客户名称筛选已做完）；
3. 识别下一步（状态筛选 + 导出）；
4. 识别一个关键决策（D-001/D-002/D-003 任意一条）；
5. 使用正确的验证命令（`./verify.sh`）。

明确告诉学员：**即使某一项没命中，demo 也不算失败**——没命中的项恰好用来讨论"工程现场还缺什么"。

### 1. Reset，看一眼起点

```bash
cd ai-rd-system-demo
./scripts/reset_d1_handoff.sh
cd workspaces/d1-handoff
cat PROGRESS.md
git log --oneline
cd ../..
```

### 2. 启动全新 Session 接手

一条命令跑完整链路并保存证据（等价于手动在 workspace 里新开一个 Codex session、只发一句接手指令）：

```bash
./scripts/d1_handoff_run.sh --no-reset
```

发给新 session 的唯一一句话（`instructor/d1/handoff/prompts/handoff.md`）：

> 接手当前任务。先判断项目现在做到哪里、当前是否健康、下一步应该做什么；确认后继续完成剩余功能，并把最新状态写回项目。

课堂如果用交互式会话代替脚本，从 `workspaces/d1-handoff/` 目录新开 Codex（不要带着之前的会话），只粘贴这一句话，不做任何补充。

`d1_handoff_run.sh` 会调用 `instructor/d1/codex_runner.py`（与 Level 1/2/3 共用同一个 runner，`--ephemeral` 保证零历史记录），把 `trace.jsonl`、`final.md`、`result.json`、`workspace.diff` 写进 `instructor/d1/handoff/results/latest/`。想看实时轨迹，可以在另一个终端：

```bash
tail -f instructor/d1/handoff/results/latest/trace.jsonl
```

### 3. 课堂应该观察什么

| 节点 | 屏幕上应该出现 | 讲师要讲的一句话 |
| --- | --- | --- |
| 读取工程状态 | 命令引用 `TASK.md`、`PROGRESS.md`、`DECISIONS.md`、`feature-list.json`、`git log` | 它没有问我们"上次做到哪了"，而是自己去项目里找 |
| 识别当前任务 | 消息里同时出现客户名称、状态、导出三个范围 | 任务边界不是我们刚才告诉它的 |
| 识别已完成项 | 消息说"客户名称筛选已完成" | 它知道哪些不用重做 |
| 识别一个决策 | 引用 D-001/D-002/D-003 或复述"权限→筛选→分页"的顺序 | 它不只读了结论，也读了原因 |
| 判断下一步 | 消息点名"状态筛选"和"导出" | 下一步来自 PROGRESS.md，不是猜的 |
| 先做健康检查 | 执行 `./verify.sh`，且发生在第一次改代码之前 | 先确认现状，再动手，这是 D0 强调过的同一个习惯 |
| 完成真实小步骤 | `app/financing/service.py`、`app/main.py` 有新增代码 | 不是只写文档，真的实现了 |
| 读取机器反馈 | 改完后再次运行 `verify.sh` 并等结果 | 反馈进入了它的收尾判断 |
| 写回工程状态 | `PROGRESS.md`、`DECISIONS.md`、`feature-list.json` 内容变化 | 下一个 session 能接着用 |
| 没有越界 | trace 里没有出现其他 workspace 或 `instructor/reference`、`instructor/golden` 路径 | 它老老实实待在自己的项目里 |

### 4. 成功时应该看到什么

```bash
cat instructor/d1/handoff/results/latest/final.md
cat instructor/d1/handoff/results/latest/result.json
```

`result.json` 里的 `predictions` 字段给出五项预测各自是否命中（附证据，不是一刀切）：

```json
{
  "1_identified_task": {"hit": true, "evidence": {"read_task_md": true, "...": "..."}},
  "2_identified_done": {"hit": true, "...": "..."},
  "3_identified_next_step": {"hit": true, "...": "..."},
  "4_identified_decision": {"hit": true, "...": "..."},
  "5_correct_verify_command": {"hit": true, "...": "..."},
  "hits": 5,
  "total": 5
}
```

`health_check_timing.ran_verify_or_pytest_before_first_edit`、`state_written_back`、`stayed_in_workspace` 分别对应"先自检""状态写回""没有越界"三项额外观察点。

## 兜底

### Session 超时或跑偏

```bash
# 1. 让学员看真实的一次成功运行（同一个 checkpoint、同一句接手指令）
cat instructor/d1/handoff/fallback/final.md
cat instructor/d1/handoff/fallback/workspace.diff
cat instructor/d1/handoff/fallback/result.json

# 2. 直接把 workspace 切到"下一步已完成"的目标状态，继续讲收口
./scripts/d1_handoff_restore_fixed.sh

# 3. 回到接手起点再演一次
./scripts/reset_d1_handoff.sh
```

`instructor/d1/handoff/fallback/` 保存的是**同一个 handoff checkpoint、同一句接手指令**下真实跑通的一次完整运行，不是另一个项目的录像；保存条件见 `instructor/d1/handoff/save_fallback.py`（五项预测必须全部命中、状态写回、没有越界）。

## Checkpoint

| Checkpoint | 命令 | 状态 |
| --- | --- | --- |
| `handoff`（baseline） | `./scripts/reset_d1_handoff.sh` | 3 个提交，客户名称筛选已完成，状态筛选/导出待做，5 passed —— 课堂正式起点 |
| `fixed` | `./scripts/d1_handoff_restore_fixed.sh` | 状态筛选 + 导出均已完成，10 passed —— 兜底展示用的目标状态 |

`d1_handoff_restore_fixed.sh` 使用讲师侧参考实现 `instructor/reference/d1-handoff-completed/`，只用于兜底，永远不进入课堂 workspace 作为起点。

## 稳定性预跑

```bash
./scripts/d1_handoff_prerun.sh 10
.venv/bin/python instructor/d1/handoff/prerun_report.py
```

结果写入 `instructor/d1/handoff/PRERUN-REPORT.md`；五项预测分别统计命中率，不做一刀切 PASS/FAIL。真实预跑数据见该报告文件，不在本 Runbook 里重复誊抄（避免和实际数据脱节）。

## D1 收口与第三讲边界

D1 只收口到"新会话能否重新建立正确的工程坐标"，不判断"状态筛选和导出做得是否符合业务标准"——那需要独立于开发侧的验收标准，是第三讲的内容。也不展示规则如何沉淀成可复用资产防止复发——那是第四讲的内容。

最后一问：

> 新 Session 靠工程现场重新找到了坐标——但它做的东西，谁来确认是对的？

第三讲回答这个问题。

---

## 补充实验｜Task → Plan → 项目环境 → 自检要求（Level 1/2/3）

> 这是原来的第二讲主 demo，现在降级为补充实验：课堂时间充足、或者想额外展示"环境逐级增加如何把临场猜测变成稳定工程输入"时使用。核心课堂链条：**先看清任务 → 再看懂项目 → 最后知道怎么交付。**

### 课前准备

在 `ai-rd-system-demo/` 根目录执行：

```bash
.venv/bin/python scripts/acceptance_check.py
(cd instructor/baselines/demo12-financing && ../../../.venv/bin/python -m pytest -q)
./scripts/d1_verify_setup.py
```

只需确认 Codex 已登录并可运行 `codex`。不需要设置额外 API key、endpoint、模型或 provider 变量；脚本直接使用当前 Codex 配置。默认单阶段 watchdog 上限为 180 秒，如需课前彩排可临时设置 `D1_TIMEOUT_SECONDS=60`，这不是课堂变量。

固定任务只有一份：

> 给融资申请列表增加客户名称和融资状态筛选，并支持导出。

旧 Demo 继续使用 `instructor/baselines/demo12-financing`；这个补充实验每一级从专用的 `instructor/baselines/d1-financing-minimal` 重置。Level 1 的 `AGENTS.md` 只保留 workspace 隔离规则，不继承旧 Demo 的代码规范、自检或 pytest 要求。独立验收器仍保留在 `instructor/d1/independent_acceptance.py`，只作为讲师课前 QA 或第三讲资产；这个补充实验课堂不调用它。

### Level 1｜Task + Plan

课堂只观察任务进入 Plan 后，模型会主动暴露哪些理解、假设、文件和风险：

```bash
./scripts/d1_plan.sh level1
```

脚本以只读 sandbox 启动 Codex，不修改代码、不执行实现、不运行 pytest，保存：

- `instructor/d1/results/latest-level1/plan.md`：Plan v1；
- `plan.trace.jsonl`、`plan.stderr`、`plan-status.json`：轨迹、错误和 watchdog 证据；
- `manifest.json`：任务哈希、baseline 数据哈希和运行信息。

课堂证明：**Plan 把原本藏在执行过程里的任务理解提前暴露出来。**

### Level 2｜Plan + 项目环境

从相同任务重新开始：

```bash
./scripts/d1_plan.sh level2
```

workspace 额外加载两项由冻结 baseline 真实整理出的环境资产：

- `PROJECT-MEMORY.md`：repository 先按 `X-User` 建立 tenant 权限范围；service 承载列表业务；已有 `ExportQueue` 但尚无融资导出 HTTP 路由；分页契约和现有测试位置；
- `CODING-STANDARDS.md`：API 层负责参数/协议，筛选进入既有 service，优先复用公共模块，保持权限/分页兼容，不引入新依赖，不做无关重构。

Codex 仍只读检查并保存 `latest-level2/plan.md`（Plan v2），不修改代码、不运行 pytest。课堂使用 `scripts/d1_compare.sh` 查看 `Plan v1 → Plan v2`：观察哪些内容从临场猜测变成了明确的模块、权限、分页、队列和文件边界决策。

### Level 3｜Plan + 项目环境 + 自检要求

先生成 Plan v3：

```bash
./scripts/d1_plan.sh level3
```

Level 3 在 Level 2 基础上增加 `SELF-CHECK.md`，要求开发侧明确检查客户名称筛选、状态筛选、组合筛选、空结果、权限、已有异步导出队列、筛选/权限上下文、pytest、`git diff --check`、`git diff --stat`、完整 diff、修改边界和最终完成说明。这里是开发侧自检，不是独立验收，更不提前使用 Golden Case。

确认大家看完 Plan v3 后，才执行真实开发：

```bash
./scripts/d1_execute.sh level3
```

这一步沿用刚才的 `workspaces/d1-level3`，使用 workspace-write sandbox，要求 Codex 按 Plan v3 开发并执行自检。保存：

- `plan.md`：Plan v3；
- `execute.trace.jsonl`、`execute.stderr`、`execute-status.json`：开发轨迹与状态；
- `final.md`：Agent 最终完成说明；
- `workspace.diff`：冻结 baseline 与实际 workspace 的可读 diff；
- `result.json`：实际修改文件、Agent 主动测试、测试结果和自检结果。

证据采集会额外运行一次 pytest 作为讲师侧开发后复核，并与 trace 中 Agent 主动运行的 pytest 分开记录；它不运行独立验收器。若测试失败，应从 trace 和最终说明确认已修复并重跑。

### 三级证据对照

三级都完成后执行：

```bash
./scripts/d1_compare.sh
```

输出不再有 winner，而是：

下面只示意表格结构；每个单元格的实际值由 Plan、trace 和 workspace evidence 动态比较得出，不预设三级一定出现某种结果。

```text
D1｜工程环境如何改变 AI 开发（补充实验）

                         Level 1    Level 2    Level 3
任务显性 Plan               YES        YES        YES
识别现有架构约束             ?          YES        YES
遵守项目代码规范             ?          YES        YES
明确修改边界                 ?          YES        YES
明确验证方式                 ?           ?         YES
实际执行代码                 NO          NO         YES
主动运行测试                 NO          NO         YES
检查 diff                    NO          NO         YES
```

并自动输出 Plan v1/v2/v3 文件、`Plan v1 → Plan v2` 与 `Plan v2 → Plan v3` unified diff，以及 Level 3 的实际修改文件、Agent 测试、测试结果、diff、自检和完成说明。

若现场需要最近一次完整证据：

```bash
./scripts/d1_save_fallback.sh
./scripts/d1_compare.sh saved
```

快照只接受三级均完成且 Level 3 已执行真实开发与自检的运行；`saved` 会明确标注 `SAVED_EVIDENCE`。Codex 超时则保留已有 trace、stderr、manifest、diff 和 elapsed。

### 补充实验收口

这个补充实验只收口到开发侧自检，不展示独立验收器，不把 Golden Case 放进课堂高潮，也不替第三讲回答产品行为是否真的可信。它和主 demo 回答的是两个不同的问题：主 demo 回答"新会话能不能找到坐标"，这个补充实验回答"环境逐级增加如何把临场猜测变成稳定输入"。两者都不替第三讲回答"现在能相信它了吗？"。
