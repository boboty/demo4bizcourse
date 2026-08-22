# AI 研发体系建设｜课堂 Demo 仓库

本仓库保留一个 Git 仓库，但课堂每个 Demo 都从自己的完整工程目录启动 Codex。不要从 `ai-rd-system-demo/` 根目录启动课堂会话，也不要让一个会话跨 Demo 继续工作。

## 目录结构

```text
workspaces/
├── demo1-vague/             融资申请基础项目；只给一句需求
├── demo2-five-elements/     同一 baseline + 五要素任务包
├── demo3-developer/         任务 B 历史错误实现 + 开发侧测试 + HTTP 黑盒服务
├── demo3-validator/         Source of Truth + Golden Case + HTTP 黑盒客户端
└── demo4-sedimentation/     正确修复状态 + 复盘输入 + 新会话变体
instructor/                  Runbook、验收脚本、Golden、角色提示和 reset 快照
handouts/                    课堂讲义
scripts/                     每个 Demo 的 reset / restore / diff 脚本
```

每个 workspace 都有自己的 `AGENTS.md`，并声明当前目录就是完整项目上下文，不读取父目录或兄弟 workspace。

## Python 环境

课堂建议使用 Python 3.11+ 的项目虚拟环境。每个 workspace 都有自己的 `pyproject.toml`、`requirements.txt` 和测试，可单独运行：

```bash
python3 -m pytest -q
```

## 课堂常用操作

```bash
# Demo 1：一句话需求由讲师从 Runbook 粘贴
./scripts/reset_demo1.sh
cd workspaces/demo1-vague
python3 -m pytest -q

# Demo 2：必须切换目录并新开会话
cd ../..
./scripts/reset_demo2.sh
cd workspaces/demo2-five-elements
python3 -m pytest -q
python3 ../../instructor/checks/task_a_acceptance.py

# Demo 3：developer 与 validator 是两个 workspace
cd ../..
./scripts/restore_demo3_wrong.sh
cd workspaces/demo3-developer
python3 -m pytest -q tests/test_settlement_developer.py
./bin/start-blackbox  # 保持 127.0.0.1:8765 运行
cd ../demo3-validator
bin/actual-output validation/cases.json  # validator 只通过 HTTP 获取实际输出

# Demo 3 修复态：停止旧服务后恢复并重新启动同一个 HTTP 接口
cd ../..
./scripts/restore_demo3_fixed.sh
cd workspaces/demo3-developer
./bin/start-blackbox
cd ../demo3-validator
bin/actual-output validation/cases.json

# Demo 4：同一 workspace，先 reset，复盘后关闭旧会话并新开会话
cd ../..
./scripts/reset_demo4.sh
```

`restore_demo2_reference.sh`、`restore_demo3_fixed.sh` 和 `restore_demo4_learned.sh` 是讲师兜底状态；普通测试不依赖其他 workspace。Demo 3 validator 的 HTTP 客户端不引用 developer 目录、源码路径或实现模块名。

## 自动验收

```bash
python3 scripts/acceptance_check.py
```

这个检查验证结构、信息边界、HTTP wrong/fixed 状态、测试和确定性 reset，不执行真实课堂 Demo，也不让 Codex 完成任务 A/B。
