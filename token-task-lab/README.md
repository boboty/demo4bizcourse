# Token Task Lab

面向课程的“任务 → 调用链 → Token”教学实验台。

它不是天津货代产品，也不是 Token 监控后台；核心目标是把同一件企业任务的正面（任务如何被接住）和背面（模型调用、工具调用、Token 读数）拆给学员看，并可替换为财务、研发、测试等其他业务场景。

## 当前范围

- 首个场景：天津货代询价（业务结构复用既有课程资产）。
- Demo 1：**本次运行的实际业务结果**（AI 实际任务理解 / 实际识别缺口 / 本次事实获取结果 /
  业务判断 / 校验 / 最终停止点），另有单独收纳的场景验收基准供对照；不展示 Token。
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

**① Demo 1 展示的是本次运行的结果，不是课前写好的答案。**
`sceanrio.known / missing / next_actions` 在任何模型调用之前就存在。它们只在
「场景验收基准」折叠区里出现，并明确标注「课前写定，不是本次 AI 的输出」；
主区域渲染的是 `observations` —— 本次 parse / gaps / facts / judge / verify / deliver
各步的真实产出。换了输入（比如改成青岛→仁川），基准会自动标注为已不适用。

**② 有结果 ≠ 能用。**
工具结果有三个状态：`missing`（无结果）/ `unverified`（有结果但不能当业务事实）/
`verified`（可核验结果）。天津船期是第二种：拿得到教学构造结构，但不构成
「可核验业务事实」，所以 C 档的「获取可核验业务事实」这一步仍然标记为 `blocked`。

**③ 真实模型调用 ≠ Token 证据齐备。**
`evidence_level=live` 只说明真的调了模型；`token_evidence` 单独记录 provider 有没有
返回 usage。`classroom_ready`（live + usage 齐备）才是「可做 Token 对比实验」的记录。
环境提示里 `saved_live_runs` 和 `classroom_ready_runs` 永远是两个分开的数字——
避免课前看到「真实运行 4 份」就以为准备完了。

## 运行

```bash
cd token-task-lab
python -m venv .venv            # 需要 Python 3.11+
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8014
```

打开 http://127.0.0.1:8014 。

**没有 API key 也能启动**：页面照常打开，可回放 `runs/` 里的记录；点「运行这一次」只会得到
结构示例（`evidence_level=structure_only`，Token 字段全部为 `null`），不会编出数字。

## 配置真实 provider

OpenAI-compatible，环境变量见 `.env.example`：

```bash
export LLM_BASE_URL=https://api.openai.com/v1   # 要含 /v1 段
export LLM_API_KEY=sk-...
export LLM_MODEL=gpt-4o-mini
export LLM_STRONG_MODEL=gpt-4o                  # 可选，D 档的「不必要的强模型」
uvicorn app.main:app --port 8014
```

`LLM_BASE_URL` 只要求能接受 `POST {base_url}/chat/completions`，
`usage` 里的 `cached_tokens` 会按 OpenAI / DeepSeek / Anthropic 几种常见写法读取；
provider 不返回缓存字段时，页面显示「provider 未返回」而不是 0。

## 课前准备：录一份可回放的运行记录

课堂默认回放已验证记录，现场真机运行只是增强。课前跑一次：

```bash
python scripts/record_runs.py          # 真实执行 A/B/C/D 并写入 runs/
python scripts/record_runs.py C D      # 只跑指定档
```

四档共用同一个 `experiment_id`，课堂上可以说清「这四条记录是同一件任务、同一批实验」。
脚本在 provider 未配置时直接退出，**不会**生成任何占位 Token 数字。跑完会打印：

- 各档的模型调用 / 工具调用 / 输入输出 Token 对比表（讲 D 档的底稿）；
- `课堂可用于 Token 实验的记录：N/M 档`。任何一档真实调了模型但 provider 没返回 usage，
  会逐档警告并**排除在这个计数之外**，脚本以非零退出码结束——不能拿它当 Token 实验记录。
  失败的调用则完全不落盘。

仓库内另存有一份 C 档结构示例记录（`evidence_level=structure_only`，Token 字段为 null），
用于确认回放链路本身可用；它不是已验证记录，别拿它讲真实用量。

## 四种模式

| 档位 | 做什么 | 课堂上看到什么 |
| --- | --- | --- |
| A 直接回答 | 只把客户原话交给模型，要求直接给可交付结果 | 1 次模型调用、0 次工具调用；模型编造或谨慎停下都成立 |
| B 全量上下文 | 一次性把当前可用资料全部塞进上下文 | 调用次数不变，输入量随资料量线性增长 |
| C 任务链 | 解析 → 判断缺口 → 获取事实 → 判断 → 校验 → 输出 | 6 个步骤、5 次模型调用、3 次工具调用；缺报价资料时停在人工确认点 |
| D 低效版本 | 同一业务目标，重复上下文、重复步骤、可选强模型 | 真实多花掉的模型调用、工具调用与输入 Token |

D 档的重复是字面意义上的重复请求，全部走真实 provider；引擎不去改任何已记录的数字。

## 结构

```
app/
  config.py            环境变量 → ProviderConfig / runs 目录
  provider.py          OpenAI-compatible 客户端 + usage 解析
  models.py            RunRecord / StepRecord / FactState / UsageSummary（场景无关）
  scenarios/           场景插件：base.py 契约 + tianjin_freight.py
  tools.py             工具调用、事实状态与计数
  engine.py            A/B/C/D 四个 runner、usage 汇总、token_evidence 判定
  store.py             runs/*.json 持久化
  views.py             front（本次实际结果 + 场景基准，无 Token）/ back 投影
  main.py              FastAPI 路由（含 /api/experiments）
runs/                  运行记录，可直接回放
scripts/record_runs.py 课前录制已验证记录
static/index.html      Demo 1 / Demo 2 / 实验对照页面
```

Demo 1 不含 Token 数字这一点是**结构性保证**：服务端把记录拆成 `front` / `back` 两半，
`front` 由字段白名单生成，`app/views.py` 里的 `FORBIDDEN_IN_FRONT` 由测试强制校验。
预设的 known/missing 也不在 `front` 顶层字段里，只能通过 `baseline` 拿到——页面想把它
当成「AI 的输出」渲染都做不到。

## API

| 路由 | 用途 |
| --- | --- |
| `GET /api/health` | provider 状态；`saved_live_runs` 与 `classroom_ready_runs` 分开报 |
| `GET /api/scenarios` | 场景目录 |
| `POST /api/runs` | 跑单档，返回 `{front, back, saved_path}` |
| `GET /api/runs` / `GET /api/runs/{id}` | 记录列表 / 回放 |
| `POST /api/experiments` | 一次跑多档，共用一个新的 `experiment_id` |
| `GET /api/experiments` / `{id}` | 对照实验列表 / 取整组 |

## 新增一个 scenario

在 `app/scenarios/` 下照 `tianjin_freight.py` 写一个模块，再在
`app/scenarios/__init__.py` 的 `SCENARIOS` 里注册一行。日志模型、引擎、存储与页面都不需要改。
