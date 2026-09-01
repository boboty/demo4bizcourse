# D1｜工程环境如何改变 AI 开发

D1 不比较工具包装，也不比较模型/provider。课堂只使用当前已经登录的 Codex / Plus 环境；模型和 provider 属于课前环境，不属于演示内容。

核心课堂链条：**先看清任务 → 再看懂项目 → 最后知道怎么交付。**

## 课前准备

在 `ai-rd-system-demo/` 根目录执行：

```bash
.venv/bin/python scripts/acceptance_check.py
(cd instructor/baselines/demo12-financing && ../../../.venv/bin/python -m pytest -q)
./scripts/d1_verify_setup.py
```

只需确认 Codex 已登录并可运行 `codex`。不需要设置额外 API key、endpoint、模型或 provider 变量；脚本直接使用当前 Codex 配置。默认单阶段 watchdog 上限为 180 秒，如需课前彩排可临时设置 `D1_TIMEOUT_SECONDS=60`，这不是课堂变量。

固定任务只有一份：

> 给融资申请列表增加客户名称和融资状态筛选，并支持导出。

旧 Demo 继续使用 `instructor/baselines/demo12-financing`；D1 每一级从专用的 `instructor/baselines/d1-financing-minimal` 重置。Level 1 的 `AGENTS.md` 只保留 workspace 隔离规则，不继承旧 Demo 的代码规范、自检或 pytest 要求。独立验收器仍保留在 `instructor/d1/independent_acceptance.py`，只作为讲师课前 QA 或第三讲资产；D1 课堂不调用它。

## Level 1｜Task + Plan

课堂只观察任务进入 Plan 后，模型会主动暴露哪些理解、假设、文件和风险：

```bash
./scripts/d1_plan.sh level1
```

脚本以只读 sandbox 启动 Codex，不修改代码、不执行实现、不运行 pytest，保存：

- `instructor/d1/results/latest-level1/plan.md`：Plan v1；
- `plan.trace.jsonl`、`plan.stderr`、`plan-status.json`：轨迹、错误和 watchdog 证据；
- `manifest.json`：任务哈希、baseline 数据哈希和运行信息。

课堂证明：**Plan 把原本藏在执行过程里的任务理解提前暴露出来。**

## Level 2｜Plan + 项目环境

从相同任务重新开始：

```bash
./scripts/d1_plan.sh level2
```

workspace 额外加载两项由冻结 baseline 真实整理出的环境资产：

- `PROJECT-MEMORY.md`：repository 先按 `X-User` 建立 tenant 权限范围；service 承载列表业务；已有 `ExportQueue` 但尚无融资导出 HTTP 路由；分页契约和现有测试位置；
- `CODING-STANDARDS.md`：API 层负责参数/协议，筛选进入既有 service，优先复用公共模块，保持权限/分页兼容，不引入新依赖，不做无关重构。

Codex 仍只读检查并保存 `latest-level2/plan.md`（Plan v2），不修改代码、不运行 pytest。课堂使用 `scripts/d1_compare.sh` 查看 `Plan v1 → Plan v2`：观察哪些内容从临场猜测变成了明确的模块、权限、分页、队列和文件边界决策。

## Level 3｜Plan + 项目环境 + 自检要求

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

## 三级证据对照

三级都完成后执行：

```bash
./scripts/d1_compare.sh
```

输出不再有 winner，而是：

下面只示意表格结构；每个单元格的实际值由 Plan、trace 和 workspace evidence 动态比较得出，不预设三级一定出现某种结果。

```text
D1｜工程环境如何改变 AI 开发

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

## D1 收口与第三讲边界

D1 只收口到开发侧自检，不展示独立验收器，不把 Golden Case 放进课堂高潮，也不替第三讲回答产品行为是否真的可信。

最后一问：

> Plan 有了，项目规则有了，自检也全绿了——现在能相信它了吗？

第三讲回答这个问题。D1 证明的是：环境逐级增加后，原来依赖模型临场猜测的东西，逐渐变成稳定的工程输入。
