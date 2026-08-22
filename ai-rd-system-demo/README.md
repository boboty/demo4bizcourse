# AI 研发体系建设｜课堂 Demo 仓库

本仓库保留一个 Git 仓库。Demo 1 与 Demo 2 共用同一个完整工程目录，课堂只改变任务交办方式；Demo 3、Demo 4 仍使用各自独立 workspace。不要从仓库根目录启动 Codex 会话。

## 目录结构

```text
workspaces/
├── demo12-financing/        Demo 1 / Demo 2 共用融资申请 baseline
├── demo3-developer/         任务 B 历史错误实现 + 开发侧测试 + HTTP 黑盒服务
├── demo3-validator/         Source of Truth + Golden Case + HTTP 黑盒客户端
└── demo4-sedimentation/     正确修复状态 + 复盘输入 + 新会话变体
instructor/                  Runbook、独立验收、Golden、角色资产和 reset 快照
handouts/                    课堂讲义
scripts/                     reset / restore / diff 脚本
```

`demo12-financing` 自带独立 `AGENTS.md`，不包含 Demo 任务文本、Spec、验收脚本、Golden 或参考实现。Demo 1 的一句话和 Demo 2 的完整 Spec 只从 `instructor/DEMO-RUNBOOK.md` 或 HTML Runbook 复制。

## Demo 1 / Demo 2 课堂入口

两次演示都使用 `workspaces/demo12-financing/`、同一 baseline、同一 `AGENTS.md`、同一 Luna + High 和同一套讲师独立验收；唯一变化是 Runbook 中的任务文本。

```bash
# Demo 1：先 reset，再进入同一 workspace，新开 Luna + High
./scripts/reset_demo1.sh
cd workspaces/demo12-financing
python3 -m pytest -q
cd ../..
python3 instructor/checks/task_a_acceptance.py
./scripts/capture_diff.sh demo1

# Demo 2：再次 reset 同一个 workspace，再新开 Luna + High
./scripts/reset_demo2.sh
cd workspaces/demo12-financing
python3 -m pytest -q
cd ../..
python3 instructor/checks/task_a_acceptance.py
./scripts/capture_diff.sh demo2
```

开发 Agent 只运行开发侧 `pytest -q`；讲师退出 workspace 后再运行独立验收。两次任务文本、课堂顺序和控制变量见 Runbook。

## 其他课堂操作

```bash
# Demo 3：developer 与 validator 是两个 workspace
./scripts/restore_demo3_wrong.sh
cd workspaces/demo3-developer
python3 -m pytest -q tests/test_settlement_developer.py
./bin/start-blackbox  # 保持 127.0.0.1:8765 运行
cd ../demo3-validator
bin/actual-output validation/cases.json

# Demo 4：同一 workspace，复盘后关闭旧会话并新开会话
cd ../..
./scripts/reset_demo4.sh
cd workspaces/demo4-sedimentation
```

## 自动验收

```bash
python3 scripts/acceptance_check.py
```

该检查验证目录隔离、Demo 1/2 共用 baseline、两次 reset 摘要一致、Demo12 无任务泄漏、Demo 3 HTTP wrong/fixed 状态、Demo 4 规则沉淀和各 workspace 测试；不执行真实课堂任务，也不让 Codex 完成任务 A/B。
