# AI 研发体系建设｜课堂 Demo 仓库

本仓库保留一个 Git 仓库，但课堂每个 Demo 都从自己的完整工程目录启动 Codex。不要从 `ai-rd-system-demo/` 根目录启动课堂会话，也不要让一个会话跨 Demo 继续工作。

## 目录结构

```text
workspaces/
├── demo1-vague/             融资申请基础项目；只给一句需求
├── demo2-five-elements/     同一 baseline + 五要素任务包
├── demo3-developer/         任务 B 历史错误实现 + 开发侧测试
├── demo3-validator/         Source of Truth + Golden Case + 黑盒验收入口
└── demo4-sedimentation/     正确修复状态 + 复盘输入 + 新会话变体
instructor/                  Runbook、验收脚本、Golden、角色提示和 reset 快照
handouts/                    课堂讲义
scripts/                     每个 Demo 的 reset / restore / diff 脚本
```

每个 workspace 都有自己的 `AGENTS.md`，并声明“当前目录就是完整项目上下文，不读取父目录或兄弟 workspace”。`instructor/` 中的讲师资产不复制进不应看到它的 workspace。

## 课堂前验证

```bash
python3 scripts/acceptance_check.py
```

这个检查只验证结构、边界、测试和确定性状态，不执行真实课堂 Demo，也不让 Codex 完成任务 A/B。

## 课堂常用操作

```bash
# Demo 1：一句话需求由讲师从 Runbook 粘贴
./scripts/reset_demo1.sh
cd workspaces/demo1-vague
pytest -q

# Demo 2：必须切换目录并新开会话
cd ../..
./scripts/reset_demo2.sh
cd workspaces/demo2-five-elements
pytest -q
python3 ../../instructor/checks/task_a_acceptance.py

# Demo 3：developer 与 validator 是两个 workspace
cd ../..
./scripts/restore_demo3_wrong.sh
cd workspaces/demo3-developer
pytest -q tests/test_settlement_developer.py
cd ../demo3-validator
pytest -q
bin/actual-output validation/cases.json  # 只取得黑盒实际输出；validator 先独立写期望

# Demo 3 修复后的确定性状态
cd ../..
./scripts/restore_demo3_fixed.sh
cd workspaces/demo3-developer
pytest -q tests/test_settlement_developer.py
cd ../demo3-validator
bin/actual-output validation/cases.json

# Demo 4：同一 workspace，先 reset，复盘后关闭旧会话并新开会话
cd ../..
./scripts/reset_demo4.sh
```

`restore_demo2_reference.sh`、`restore_demo3_fixed.sh` 和 `restore_demo4_learned.sh` 是讲师兜底状态；普通测试不依赖其他 workspace。

## 业务素材边界

- Demo 1 只有融资申请基础代码和基础测试，一句话需求只在 Runbook 中出现。
- Demo 2 在相同 baseline 上增加现有五要素任务包；独立验收脚本仍在 `instructor/`。
- Demo 3 validator 通过 `bin/actual-output` 黑盒入口取实际结果，不复制 developer 源码。
- Demo 4 初始 `AGENTS.md` 没有双候选规则；复盘后写入 `AGENTS.md` 与 `validation/checklist.md`，新会话只读取项目级规则完成变体任务。
