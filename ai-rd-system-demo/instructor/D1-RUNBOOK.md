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

**Harness A：裸执行 Harness。** 只提供 Codex CLI 的标准文件与终端能力；Agent 自己发现项目结构、组织步骤、运行检查和控制改动范围。

**Harness B：工程工作台 Harness。** 保留与 A 完全相同的业务源码、`AGENTS.md` 和任务文本，但额外提供非业务化的工作台工具：项目结构索引、计划记录、开发测试快捷命令和 baseline diff。工具不包含接口规则、验收条件、答案或参考实现；它改变的是环境内的上下文组织和执行/验证能力，而不是交给模型的业务 Prompt。

两边都使用同一个 `codex exec`、同一模型、同一推理档位、相同 `workspace-write` 沙箱和相同自动审批配置。每次运行的 `manifest.json` 会记录 task、数据、冻结 baseline 和 reset 后工作区的哈希，以及模型和档位；对照脚本会先校验它们一致。

## 课堂执行

从 `ai-rd-system-demo/` 根目录执行。首次只需确认已登录 Codex；无需在课堂安装 Python 包或访问 PyPI。

```bash
# 1. 明确锁定本场的模型和推理档位（两次必须相同）
export D1_MODEL='gpt-5.6-luna'
export D1_REASONING_EFFORT='high'

# 2. 依次运行 A、B；脚本自己 reset、投喂完全相同的一句话并捕获 JSONL 工具轨迹
./scripts/d1_run.sh a
./scripts/d1_run.sh b

# 3. 一条命令投屏对照证据
./scripts/d1_compare.sh
```

如果要由讲师手动操作而不启动模型，先运行 `./scripts/reset_d1.sh both`，再分别从 `workspaces/d1-harness-a` 和 `workspaces/d1-harness-b` 启动相同模型/档位的 Codex，并**只**粘贴上面的固定任务。完成后以各自 trace 和 manifest 运行 `instructor/d1/capture.py`；常规课堂优先使用 `d1_run.sh`，因为它能消除手工粘贴、模型参数和日志采集的偏差。

## 如何展示

`d1_compare.sh` 会在一张表中展示：首次读取的上下文、计划证据、工程工具调用、Agent 是否主动运行开发测试、修改文件、最终开发测试、独立业务验收、越界修改和最终结论。详细原始证据在 `instructor/d1/results/`：每次的 CLI JSONL trace、运行 manifest 和结构化结果。

独立验收器在 `instructor/d1/independent_acceptance.py`，不会复制进 A/B 工作区；它覆盖客户名模糊筛选、状态精确筛选、单/多条件、空结果、权限范围、异步导出及其筛选/权限 payload、严格字段和前端能力，并同时检查修改边界。

实验结果不是预设 A 必败或 B 必胜。表格只呈现本次运行的行为与事实；两组都失败、都通过或呈现不同改动路径，都是可讨论的真实证据。
