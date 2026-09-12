# AGENTS.md — Token Task Lab

本目录是独立课程 Demo。实现时只围绕教学目标，不把它扩成货代业务系统。

## 核心教学目标

让学员看见：

1. 一句自然语言如何被翻译成一件业务任务；
2. 为什么一件业务任务不等于一次模型调用；
3. 同一任务在不同执行方式下，Token 为什么不同；
4. 哪些 Token 属于完成任务必须付出的有效工作量，哪些属于低效消耗。

## 场景与结构

首个 scenario 为 `tianjin-freight`，但架构必须允许后续增加：

- finance
- software-rd
- testing
- document-analysis

不要把 UI、运行逻辑、日志字段写死在“船期/报价”业务上。

## Demo 1 与 Demo 2 必须共用同一次运行资产

### Demo 1｜业务正面

只展示：

- 原始需求
- 任务理解
- 已知条件
- 缺失条件
- 下一步动作
- 工具/资料依赖
- 人工确认点

禁止在 Demo 1 主界面展示 Token 数字。

### Demo 2｜运行背面

从 Demo 1 的同一次 run_id 进入“查看运行过程”，展示：

- step
- action
- model
- input_tokens
- output_tokens
- cached_tokens（provider 有则展示，没有则 null）
- tool_calls
- latency_ms
- result/status
- finish_reason（provider 报的结束原因；缺失记为 unknown，不当作完整）
- 输出是否被长度上限截断（截断的步骤必须明确标出，不能让学员误以为是完整结果）

页首同时显示：业务侧 `1 件任务`，系统侧实际模型调用次数、工具调用次数、Token 合计。

## A/B/C/D 实验模式

所有数字必须由真实调用日志生成，不允许手填 Token 数字。

- A 直接回答：只给客户原始输入，要求形成可交付结果。模型若编造，现场验货；模型若谨慎停下，同样成立。
- B 全量上下文：一次性加入当前可用业务资料，观察任务质量与输入量变化。
- C 任务链：按“解析 → 判断缺口 → 获取事实 → 判断 → 校验 → 输出”执行；这是主版本。
- D 低效版本：在保持同一业务目标的前提下，故意重复上下文、使用不必要的强模型或重复步骤；必须真实执行，不能修改日志数字。

## 真实性边界

- 不得把未经验证来源的船期、运价、舱位写成真实业务事实。
- 如果缺报价资料，任务应明确停在“报价待业务资料/人工确认”。
- 教学用结构化资料如需构造，必须标注 `teaching_fixture`，不得在课堂文案中暗示为真实客户数据。
- Token、耗时、缓存命中必须来自 provider 返回值或本地实测。
- 输出是否完整同样只能来自 provider 的 `finish_reason`：没有这个字段就只能记
  `unknown`，不得推断为完整，也不得为了让数字好看而调大 `max_tokens`。

## Provider

实现 OpenAI-compatible 配置，至少支持环境变量：

- `LLM_BASE_URL`
- `LLM_API_KEY`
- `LLM_MODEL`

不要把任何密钥提交进仓库。

## 运行记录

每次运行生成 `run_id`，记录原始请求、scenario、mode、steps、usage、输出与异常。课堂默认回放已验证记录；现场真机运行只是增强。

## 验收

1. `pytest` 通过。
2. 无 API key 时 Demo 仍可启动，并能回放本地记录/结构示例。
3. 有 API key 时能真实运行并留存 usage。
4. Demo 1 页面不泄露 Token；Demo 2 可从同一 run_id 打开背面。
5. D 模式的高消耗必须来自真实执行。
6. 场景层与实验引擎解耦，新增第二个 scenario 不需要改核心日志模型。
