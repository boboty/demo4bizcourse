# AI 研发体系建设｜课堂 Demo 仓库

本仓库保留一个 Git 仓库，但课堂每个 Demo 都从自己的完整工程目录启动 Codex。不要从 `ai-rd-system-demo/` 根目录启动课堂会话，也不要让一个会话跨 Demo 继续工作。

- **任务 A（Demo 1 → Demo 2）**：融资申请列表筛选 + 导出。用于证明“模糊需求”和“五要素可交办任务”的差别。
- **任务 B（Demo 3 → Demo 4）**：汇损 + 退税双候选。用于证明“同源验证抓不到共同理解偏差”，以及如何把教训沉淀进项目规则。

Demo 1 的前 5 分钟使用外部 CNN 可视化页面，不在本仓库内：
https://adamharley.com/nn_vis/cnn/3d.html

## Python 环境要求

> **建议始终使用项目自己的 `.venv`，不要把依赖安装进 macOS 系统 Python。**
>
> 本仓库代码使用 `X | None` 等 Python 3.10+ 语法，因此 **Python 3.9 不支持**。课堂统一使用 **Python 3.12**，与仓库内离线 wheel 的验证环境保持一致。

### 首次准备这台 Mac

```bash
cd ai-rd-system-demo
brew install python@3.12   # 已安装可跳过
rm -rf .venv              # 仅首次重建环境时执行
"$(brew --prefix python@3.12)/bin/python3.12" -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -r requirements.txt
```

确认虚拟环境：

```bash
which python
python --version
which pytest
```

正常情况下：

- `python` 和 `pytest` 都应指向当前项目的 `.venv/`；
- `python --version` 应显示 Python 3.12.x；
- 不要使用 macOS 系统自带的 Python 3.9.x。

### 已经创建过 `.venv` 时

以后彩排或上课前不需要重新安装，只需：

```bash
cd ai-rd-system-demo
source .venv/bin/activate
./scripts/reset_base.sh
pytest -q
open instructor/DEMO-RUNBOOK.html
```

### 离线安装

```bash
rm -rf .venv
"$(brew --prefix python@3.12)/bin/python3.12" -m venv .venv
source .venv/bin/activate
python -m pip install --no-index --find-links vendor/wheels -r requirements.lock.txt
pytest -q
```

离线 wheel 以 **Python 3.12 + macOS Apple Silicon** 为验证目标；其他 Python 版本或平台需要联网重新生成 `vendor/wheels/`。

## 快速启动应用

```bash
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

浏览器打开 http://127.0.0.1:8000

## 彩排基线检查

```bash
git status
pytest -q
python instructor/checks/task_a_acceptance.py
python validation/independent_check.py
```

预期结果：

- `git status`：工作区干净；
- `pytest -q`：5 个开发侧测试全绿；
- 任务 A：基线尚未完成五要素任务，独立验收应为 **BLOCKER**；
- 任务 B：基线故意保留“开发测试全绿、业务理解错误”的历史状态，独立验收应在 GC-01 抓出 **BLOCKER**。

这正是 Demo 2 与 Demo 3 后续要展示的对照基础。

> 当前依赖组合可能出现 Starlette/httpx 的 deprecation warning；只要测试仍为 PASS，不影响本课程 Demo。

## 课堂常用命令

```bash
# 恢复到课前基线：任务 A 未实现；任务 B 处于“错误但测试全绿”状态
./scripts/reset_base.sh

# 保存 Demo 1 / Demo 2 的现场 diff
./scripts/capture_diff.sh demo1
./scripts/capture_diff.sh demo2

# 运行任务 A 的独立验收（Demo 2 完成后）
python instructor/checks/task_a_acceptance.py

# 任务 B：开发侧测试，全绿
pytest -q tests/test_settlement_developer.py

# 任务 B：黑盒输出
python -m app.settlement.cli validation/cases.json

# 任务 B：确定性独立验收兜底（错误状态应 FAIL）
python validation/independent_check.py

# 如现场 Codex 恰好把任务 B 做对了，可透明切回预置的“历史错误运行”状态
./scripts/restore_demo3_wrong.sh

# Demo 2 参考解（现场 Codex 卡住时透明切换）
./scripts/restore_demo2_reference.sh

# Demo 3 修复后的确定性状态
./scripts/restore_demo3_fixed.sh

# Demo 4 复盘沉淀后的确定性状态
./scripts/restore_demo4_learned.sh
```

## Codex 与 AGENTS.md

根目录 `AGENTS.md` 是项目級规则入口。Demo 4 前它**没有**“双候选优先”规则；复盘角色要把这次教训写进去。然后必须新开 Codex 会话，让新会话重新加载规则，再做变体任务。

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
