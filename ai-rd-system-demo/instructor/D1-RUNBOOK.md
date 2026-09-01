# D1｜同模型、同任务、两个 Harness 对照实验

这个实验只证明一件事：模型、任务和业务工程都不变时，模型被放进的工程工作环境会改变其研发行为与可验证结果。它不是工具强弱、Prompt 长短、UI 或速度的比较。

## 受控变量

- 相同融资申请 baseline：`instructor/baselines/demo12-financing`。
- 相同业务数据、相同一句任务、相同模型和推理档位。
- 相同开发侧测试命令和同一个工作区外独立验收器。
- 每次运行先由 reset 从该 baseline 创建两个互不共享文件的工作区。

固定任务文本（A/B 一字不变）：

> 给融资申请列表增加客户名称和融资状态筛选，并支持导出。

## 两个 Harness

**Harness A：Generic Model / Chat Harness。** 通过标准库调用 Responses API，`tools=[]`，不给 shell、文件写入、pytest 或 terminal。模型从确定性 `source_bundle.json` 阅读冻结源码，只输出分析、计划和 patch 建议，不写回工作区。

**Harness B：Coding Harness。** 使用原生 Codex Coding Harness 读取真实 workspace、搜索、修改、运行命令、测试和查看 diff；不复制任何 D1 专用提示或 helper 文件。

两边使用同一模型、推理档位、任务文本、业务数据、冻结 baseline 和 workspace 外独立验收器。A 额外记录 source bundle hash；B 记录 reset 后 workspace hash；对照脚本会校验二者对应同一 baseline。两边的工具能力有意不同，这是本实验唯一主要变量。

## 课堂执行

从 `ai-rd-system-demo/` 根目录执行。首次只需确认已登录 Codex；无需在课堂安装 Python 包或访问 PyPI。

```bash
# 1. 明确锁定本场的模型和推理档位（两次必须相同）
export D1_MODEL='gpt-5.6-luna'
export D1_REASONING_EFFORT='high'

# 2. 依次运行 A、B；脚本自己 reset、投喂完全相同的一句话并捕获证据
./scripts/d1_run.sh a
./scripts/d1_run.sh b

# 3. 一条命令投屏对照证据
./scripts/d1_compare.sh
```

A 的源码上下文存为运行目录内的 `source_bundle.json`，不进入用户任务 input；B 只使用 reset 后的真实 workspace。若 A 的 API key 或模型权限不可用，脚本仍会保存失败响应和 manifest，compare 会明确显示失败，不得降级为 Coding Harness。

## 如何展示

`d1_compare.sh` 会在一张表中展示：模型、任务、baseline、是否可检查/修改/执行、上下文来源、计划/提案、修改文件、测试、独立业务验收和最终结论。详细原始证据在 `instructor/d1/results/`：A 的 source bundle、Responses raw response 和提案；B 的 CLI JSONL trace、manifest 和结构化结果。

独立验收器在 `instructor/d1/independent_acceptance.py`，不会复制进 A/B 工作区；它覆盖客户名模糊筛选、状态精确筛选、单/多条件、空结果、权限范围、异步导出及其筛选/权限 payload、严格字段和前端能力，并同时检查修改边界。

实验结果不是预设 A 必败或 B 必胜。表格只呈现本次运行的行为与事实；两组都失败、都通过或呈现不同改动路径，都是可讨论的真实证据。
