# AI 研发体系建设｜课堂 Demo 仓库

这是一套为一天版课程准备的 **Codex 真机演示仓库**。全天使用同一个研发世界，但分成两条任务线：

- **任务 A（Demo 1 → Demo 2）**：融资申请列表筛选 + 导出。用于证明“模糊需求”和“五要素可交办任务”的差别。
- **任务 B（Demo 3 → Demo 4）**：汇损 + 退税双候选。用于证明“同源验证抓不到共同理解偏差”，以及如何把教训沉淀进项目规则。

Demo 1 的前 5 分钟使用外部 CNN 可视化页面，不在本仓库内：
https://adamharley.com/nn_vis/cnn/3d.html

## 快速开始

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
pytest -q
uvicorn app.main:app --reload --port 8000
```

浏览器打开 http://127.0.0.1:8000

### 离线安装

现场断网时可使用仓库内的锁定依赖和 wheel 缓存：

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --no-index --find-links vendor/wheels -r requirements.lock.txt
pytest -q
```

离线 wheel 以 Python 3.12 + macOS Apple Silicon 为验证目标；其他 Python 版本或平台需要联网重新生成 `vendor/wheels/`。

默认测试应当全绿。

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

根目录 `AGENTS.md` 是项目级规则入口。Demo 4 前它**没有**“双候选优先”规则；复盘角色要把这次教训写进去。然后必须新开 Codex 会话，让新会话重新加载规则，再做变体任务。

## 目录

```text
app/                    可运行的小型研发项目
static/                 简单前端
tests/                  开发侧测试
tasks/                  课堂任务输入
prompts/                Codex / 作战室角色提示
rules/                  Source of Truth（任务 B）
validation/             独立验收输入与工具
instructor/             讲师 runbook、兜底、验收脚本
handouts/               学员实战讲义
scripts/                reset / capture / restore
```

> 设计原则：Demo 不是展示 Codex 有多少功能，而是给课程判断提供证据。
