# Token Task Lab

面向课程的“任务 → 调用链 → Token”教学实验台。

它不是天津货代产品，也不是 Token 监控后台；核心目标是把同一件企业任务的正面（任务如何被接住）和背面（模型调用、工具调用、Token 读数）拆给学员看，并可替换为财务、研发、测试等其他业务场景。

## 当前范围

- 首个场景：天津货代询价（业务结构复用既有课程资产）。
- Demo 1：看任务拆解、已知/缺失条件、人工确认点；不展示 Token。
- Demo 2：翻到同一次运行的背面，展示调用步骤和 Token 字段。
- A/B/C/D 四种实验模式的 UI 与数据契约预留。
- 未经来源验证的船期、运价不得作为真实事实写入；当前骨架不内置伪造 Token 数字。

## 教学原则

1. 同一件任务一路追到底，不做三个孤立节目。
2. Demo 1 看业务结构，Demo 2 看调用结构。
3. 所有 Token 数字必须来自真实运行日志；低效版本也必须真跑。
4. 允许模型停下来：缺资料、缺权限、缺事实都是教学内容，不追求“完美跑通”。
5. 记录是主，真机是彩蛋：课堂必须能回放一份经过验证的运行记录。

## 运行

```bash
cd token-task-lab
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8014
```

打开 http://127.0.0.1:8014 。

## 后续实现目标

详见 `AGENTS.md`。下一阶段由编码 Agent 完成：

- OpenAI-compatible provider 接入；
- A/B/C/D 四种真实运行模式；
- usage/token/cached token/latency/tool call 留痕；
- 运行记录持久化与课堂回放；
- 场景插件化，天津货代只是第一个 scenario。
