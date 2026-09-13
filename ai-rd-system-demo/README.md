# AI 研发体系建设｜课堂 Demo 仓库

本仓库保留一个 Git 仓库。Demo 1 与 Demo 2 共用同一个完整工程目录，课堂只改变任务交办方式；D0、Demo 3、Demo 4 使用各自独立 workspace。不要从仓库根目录启动 Agent 会话。

## 目录结构

```text
workspaces/
├── d0-first-loop/           第一讲连续执行：半成品还款计划 + 真实红灯
├── demo12-financing/        Demo 1 / Demo 2 共用融资申请 baseline
├── demo3-developer/         任务 B 历史错误实现 + 开发侧测试 + HTTP 黑盒服务
├── demo3-validator/         Source of Truth + Golden Case + HTTP 黑盒客户端
└── demo4-sedimentation/     正确修复状态 + 复盘输入 + 新会话变体
instructor/                  Runbook、独立验收、Golden、角色资产和 reset 快照
handouts/                    课堂讲义
scripts/                     reset / restore / diff 脚本
```

`demo12-financing` 自带独立 `AGENTS.md`，不包含 Demo 任务文本、Spec、验收脚本、Golden 或参考实现。Demo 1 的一句话和 Demo 2 的完整 Spec 只从 `instructor/DEMO-RUNBOOK.md` 或 HTML Runbook 复制。

## D0｜连续执行（第一讲）

D0 只证明一件事：Agent 能在真实反馈下连续工作——先跑验证，读到失败，再读取项目和测试定位问题、修改代码，并复跑直到通过。工程环境、独立验证、规则沉淀都不在 D0 里，它们是 D1／第三讲／第四讲的内容。

```bash
./scripts/reset_d0.sh                     # 起点固定为 4 failed, 4 passed
cd workspaces/d0-first-loop
../../.venv/bin/python -m pytest -q       # 现场确认红灯
cd ../..
./scripts/d0_run.sh                       # 启动 Agent 并保存 trace / diff / result.json
```

完整课堂流程、观察点、兜底与 checkpoint 见 [instructor/D0-RUNBOOK.md](instructor/D0-RUNBOOK.md)。课前 QA 用 `scripts/d0_verify.py`，稳定性证据见 `instructor/d0/PRERUN-REPORT.md` 与 `instructor/d0/fallback/`。

## D1｜工程现场接力：新会话如何找到自己的坐标

D1 的主 demo 证明：一个没有上一轮聊天记录的全新 Agent Session，仍然能从 `TASK.md`／`PROGRESS.md`／`DECISIONS.md`／`feature-list.json`／`verify.sh`／Git History 里重新找到当前任务、已完成项、关键决策和下一步，并把状态写回去。课堂只使用已经登录的 Codex / Plus 环境；模型和 provider 是课前环境，不是 D1 的比较变量。完整课堂入口见 [instructor/D1-RUNBOOK.md](instructor/D1-RUNBOOK.md)。

```bash
./scripts/reset_d1_handoff.sh
./scripts/d1_handoff_run.sh --no-reset
```

课前可运行 `scripts/d1_handoff_verify_setup.py` 做不调用模型的 reset、环境资产和边界预检；稳定性预跑见 `scripts/d1_handoff_prerun.sh` 与 `instructor/d1/handoff/PRERUN-REPORT.md`。

原来的 Task → Plan → 项目环境 → 自检要求 三级对比实验（Level 1/2/3）降级为补充实验，保留在 `instructor/D1-RUNBOOK.md` 末尾：

```bash
./scripts/d1_plan.sh level1
./scripts/d1_plan.sh level2
./scripts/d1_plan.sh level3
./scripts/d1_execute.sh level3
./scripts/d1_compare.sh
```

## 环境

全课统一使用仓库根目录 `ai-rd-system-demo/.venv` 和 Python 3.12；不为 workspace 创建独立 venv，也不污染系统 Python。首次准备：

```bash
cd ai-rd-system-demo
brew install python@3.12  # 已安装可跳过
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt
which python
python --version
which pytest
```

每次彩排/上课前运行：

```bash
cd ai-rd-system-demo
source .venv/bin/activate
which python
python --version
python scripts/acceptance_check.py
```

若 import 失败，首先检查是否使用根目录 `.venv`；不要临时 `pip install`，也不要在课堂中访问 PyPI 修环境。

## Demo 1 / Demo 2 课堂入口

两次演示都使用 `workspaces/demo12-financing/`、同一 baseline、同一 `AGENTS.md`、同一 Luna + High 和同一套讲师独立验收；唯一变化是 Runbook 中的任务文本。

```bash
# Demo 1：先 reset，再进入同一 workspace，新开 Luna + High
./scripts/reset_demo1.sh
cd workspaces/demo12-financing
../../.venv/bin/python -m pytest -q
cd ../..
.venv/bin/python instructor/checks/task_a_acceptance.py
./scripts/capture_diff.sh demo1

# Demo 2：再次 reset 同一个 workspace，再新开 Luna + High
./scripts/reset_demo2.sh
cd workspaces/demo12-financing
../../.venv/bin/python -m pytest -q
cd ../..
.venv/bin/python instructor/checks/task_a_acceptance.py
./scripts/capture_diff.sh demo2
```

开发 Agent 只运行开发侧 `../../.venv/bin/python -m pytest -q`；讲师退出 workspace 后再运行独立验收。两次任务文本、课堂顺序和控制变量见 Runbook。

## 其他课堂操作

```bash
# Demo 3：developer 与 validator 是两个 workspace
./scripts/restore_demo3_wrong.sh
cd workspaces/demo3-developer
../../.venv/bin/python -m pytest -q tests/test_settlement_developer.py
./bin/start-blackbox  # 保持 127.0.0.1:8765 运行
cd ../demo3-validator
../../.venv/bin/python bin/actual-output validation/cases.json

# Demo 4：同一 workspace，复盘后关闭旧会话并新开会话
cd ../..
./scripts/reset_demo4.sh
cd workspaces/demo4-sedimentation
```

## 自动验收

```bash
.venv/bin/python scripts/acceptance_check.py
```

该检查验证目录隔离、D0 reset／起点红灯／目标状态、Demo 1/2 共用 baseline、两次 reset 摘要一致、Demo12 无任务泄漏、Demo 3 HTTP wrong/fixed 状态、Demo 4 规则沉淀和各 workspace 测试；不执行真实课堂任务，也不让 Agent 完成任务 A/B。

D0 单独课前 QA：

```bash
.venv/bin/python scripts/d0_verify.py
```

`d0-first-loop` 的起点故意包含真实的失败测试，因此不进入上面的"standalone pytest"全绿清单。
