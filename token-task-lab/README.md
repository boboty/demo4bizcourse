# Token Task Lab

面向课程的“任务 → 调用链 → Token”教学实验台。

它不是天津货代产品，也不是 Token 监控后台；核心目标是把同一件企业任务的正面（任务如何被接住）和背面（模型调用、工具调用、Token 读数）拆给学员看，并可替换为财务、研发、测试等其他业务场景。

## 当前范围

- 首个场景：天津货代询价（业务结构复用既有课程资产）。
- Demo 1：**本次运行的实际业务结果**（AI 实际任务理解 / 实际识别缺口 / 本次事实获取结果 / 业务判断 / 校验 / 最终停止点），另有单独收纳的场景验收基准供对照；不展示 Token。
- Demo 2：从同一 `run_id` 翻到运行背面，展示调用步骤、usage、缓存与耗时。
- A/B/C/D 四种模式均为真实执行；低效版本也是真跑，不修改日志数字。
- 未经来源验证的船期、运价不得作为真实事实写入；构造资料一律标注 `teaching_fixture`。

## 教学原则

1. 同一件任务一路追到底，不做三个孤立节目。
2. Demo 1 看业务结构，Demo 2 看调用结构。
3. 所有 Token 数字必须来自真实运行日志；低效版本也必须真跑。
4. 允许模型停下来：缺资料、缺权限、缺事实都是教学内容，不追求“完美跑通”。
5. 记录是主，真机是彩蛋：课堂必须能回放一份经过验证的运行记录。

## 三条不能破的课程不变量

这三条都有测试强制（`tests/test_course_invariants.py`），改动核心逻辑时会挡住回归：

**① Demo 1 展示的是本次运行的结果，不是课前写好的答案。** 预设 `known / missing / next_actions` 只出现在「场景验收基准」里；主区域渲染本次 `parse / gaps / facts / judge / verify / deliver` 的真实产出。

**② 有结果 ≠ 能用。** 工具结果分 `missing` / `unverified` / `verified` 三种状态；天津船期是“有结果但未核验”，因此仍不能作为可核验业务事实。

**③ 真实模型调用 ≠ Token 证据齐备。** `evidence_level=live` 只说明真的调了模型；`classroom_ready` 只有在 usage 齐备时才成立。

## 课堂固定 Provider

本课程 Demo 固定使用 DeepSeek：

- Base URL：`https://api.deepseek.com`
- Model：`deepseek-flash`
- 课堂唯一必填：`LLM_API_KEY`

Base URL 和模型写死在 `app/config.py`，不在课堂临时切换。

## 运行

```bash
cd token-task-lab
python -m venv .venv            # 需要 Python 3.11+
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # 首次运行时做一次
# 编辑 .env，只填 LLM_API_KEY
uvicorn app.main:app --reload --port 8014
```

`app/config.py` 会自动加载 `token-task-lab/.env`。如果 shell 里已经显式 `export` 了同名变量，则 shell 值优先。

课堂建议直接打开：

```text
http://127.0.0.1:8014/runbook
```

没有 API Key 也能启动：页面照常打开，可回放 `runs/` 里的记录；点“运行这一次”只会得到结构示例，不会编 Token 数字。

## 课前准备：录一份可回放的运行记录

`.env` 已经填好 API Key 后，直接运行：

```bash
python scripts/record_runs.py          # 真实执行 A/B/C/D 并写入 runs/
python scripts/record_runs.py C D      # 只跑指定档
```

四档共用同一个 `experiment_id`。最后必须看到：

```text
课堂可用于 Token 实验的记录：4/4 档
```

否则不要把这一组数字作为 Token 课堂证据。

## 四种模式

| 档位 | 做什么 | 课堂上看到什么 |
| --- | --- | --- |
| A 直接回答 | 只把客户原话交给模型，要求直接给可交付结果 | 1 次模型调用、0 次工具调用；模型编造或谨慎停下都成立 |
| B 全量上下文 | 一次性把当前可用资料全部塞进上下文 | 调用次数不变，输入量随资料量增长 |
| C 任务链 | 解析 → 判断缺口 → 获取事实 → 判断 → 校验 → 输出 | 6 个步骤、5 次模型调用、3 次工具调用；缺报价资料时停在人工确认点 |
| D 低效版本 | 同一业务目标，重复上下文、重复步骤、可选强模型 | 真实多花掉的模型调用、工具调用与输入 Token |

D 档的重复全部走真实 provider；引擎不修改任何已记录数字。

## 本地环境文件

`token-task-lab/.gitignore` 会忽略本 Demo 下的 `.env`、`.env.*` 以及子目录中的同类文件；`.env.example` 例外，继续作为模板提交到仓库。API Key 不应进入 Git。

## 结构

```text
app/
  config.py            固定 DeepSeek Base URL / model，自动加载 .env
  provider.py          OpenAI-compatible 客户端 + usage 解析
  models.py            RunRecord / StepRecord / FactState / UsageSummary
  scenarios/           场景插件
  tools.py             工具调用、事实状态与计数
  engine.py            A/B/C/D runner、usage 汇总、token_evidence 判定
  store.py             runs/*.json 持久化
  views.py             front / back 投影
  main.py              FastAPI 路由（含 /api/experiments 与 /runbook）
runs/                  运行记录，可直接回放
scripts/record_runs.py 课前录制已验证记录
static/index.html       Demo 页面
static/runbook.html     讲师单页驾驶舱
```

## API

| 路由 | 用途 |
| --- | --- |
| `GET /api/health` | provider 状态；真实运行与 classroom-ready 分开报 |
| `GET /api/scenarios` | 场景目录 |
| `POST /api/runs` | 跑单档 |
| `GET /api/runs` / `GET /api/runs/{id}` | 记录列表 / 回放 |
| `POST /api/experiments` | 一次跑多档，共用一个 `experiment_id` |
| `GET /api/experiments` / `{id}` | 对照实验列表 / 取整组 |

## 新增一个 scenario

在 `app/scenarios/` 下照 `tianjin_freight.py` 写一个模块，再在 `app/scenarios/__init__.py` 的 `SCENARIOS` 里注册一行。日志模型、引擎、存储与页面都不需要改。
