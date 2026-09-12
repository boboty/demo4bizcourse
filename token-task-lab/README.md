# Token Task Lab

面向课程的“任务 → 调用链 → Token”教学实验台。

它不是天津货代产品，也不是 Token 监控后台；核心目标是把同一件企业任务的正面（任务如何被接住）和背面（模型调用、工具调用、Token 读数）拆给学员看，并可替换为财务、研发、测试等其他业务场景。

## 当前范围

- 首个场景：天津货代询价（业务结构复用既有课程资产）。
- Demo 1：看任务拆解、已知/缺失条件、下一步动作、工具/资料依赖、人工确认点；**不展示 Token**。
- Demo 2：从同一 `run_id` 翻到运行背面，展示调用步骤、usage、缓存与耗时。
- A/B/C/D 四种模式均为真实执行；低效版本也是真跑，不修改日志数字。
- 未经来源验证的船期、运价不得作为真实事实写入；构造资料一律标注 `teaching_fixture`。

## 教学原则

1. 同一件任务一路追到底，不做三个孤立节目。
2. Demo 1 看业务结构，Demo 2 看调用结构。
3. 所有 Token 数字必须来自真实运行日志；低效版本也必须真跑。
4. 允许模型停下来：缺资料、缺权限、缺事实都是教学内容，不追求“完美跑通”。
5. 记录是主，真机是彩蛋：课堂必须能回放一份经过验证的运行记录。

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

脚本在 provider 未配置时直接退出，**不会**生成任何占位 Token 数字。跑完会打印各档对比表，
可直接用来核对「D 档确实比 C 档贵在哪里」。

仓库内已保存一份 C 档结构示例记录（`evidence_level=structure_only`，无 Token 数字），
用于无网络、无 provider 时确认回放链路可用。

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
  models.py            RunRecord / StepRecord / UsageSummary（场景无关）
  scenarios/           场景插件：base.py 契约 + tianjin_freight.py
  tools.py             工具调用与计数
  engine.py            A/B/C/D 四个 runner、usage 汇总
  store.py             runs/*.json 持久化
  views.py             front（业务正面，无 Token）/ back（运行背面）投影
  main.py              FastAPI 路由
runs/                  运行记录，可直接回放
scripts/record_runs.py 课前录制已验证记录
static/index.html      Demo 1 / Demo 2 页面
```

Demo 1 不含 Token 数字这一点是**结构性保证**：服务端把记录拆成 `front` / `back` 两半，
`front` 由字段白名单生成，`app/views.py` 里的 `FORBIDDEN_IN_FRONT` 由测试强制校验。

## 新增一个 scenario

在 `app/scenarios/` 下照 `tianjin_freight.py` 写一个模块，再在
`app/scenarios/__init__.py` 的 `SCENARIOS` 里注册一行。日志模型、引擎、存储与页面都不需要改。
