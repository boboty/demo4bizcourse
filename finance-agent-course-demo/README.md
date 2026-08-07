# 企业 AI 大模型与智能体课程财务演示套件 V1.0

本项目服务于《企业AI大模型与智能体：选型、落地与产研赋能》课程，是一套可离线运行的财务业务演示。所有业务数据、知识检索、工具调用、智能体判断和结账结果均为固定构造数据，不是真实财务处理系统。

## 演示内容

| 序号 | 页面 | 主题 | 建议时长 |
|---|---|---|---|
| 1 | `/demo/knowledge-answer` | 通用模型与企业知识回答对比 | 8 分钟 |
| 2 | `/demo/batch-workflow` | 40 笔银行流水固定工作流 | 8 分钟 |
| 3 | `/demo/exception-agent` | 异常流水调查、证据不足停止、人工介入 | 15 分钟 |
| 4 | `/demo/independent-validation` | 实现和测试全绿但业务规则理解错误 | 10 分钟 |
| 5 | `/demo/month-close` | 人工确认后按确定性规则结转损益并结账 | 5 分钟 |

建议课堂顺序：知识依据 → 固定工作流 → 异常智能体 → 独立验收 → 传统系统自动化。

## 技术栈

- Python 3.11+
- FastAPI、Uvicorn、pytest、httpx
- 原生 HTML、CSS、JavaScript
- 无数据库、无前端构建工具、无真实模型调用
- 所有业务数据来自 `app/fixtures/` 和 `app/static/shared/scenario-data.js`

## 安装与启动

```bash
./scripts/setup.sh
./scripts/run.sh
```

默认监听 `http://127.0.0.1:8001`，总览页为 `http://127.0.0.1:8001/demo`。端口可通过 `PORT` 覆盖：

```bash
PORT=8015 ./scripts/run.sh
```

单独打开任一演示即可录屏；页面通过公共控制器支持上一步、下一步、自动播放、暂停、继续、重新开始、任意步骤跳转和直接显示最终结果。

## 离线与安全边界

- 运行时不请求外部网络、不加载 CDN、不使用在线字体。
- 页面内的“知识检索”“工具调用”“智能体调查”是预设状态展示。
- AI 不能自动核销有歧义的应收，不能修改原始单据，不能自动过账，不能替代会计做最终业务判断。
- 结账演示必须先经过人工确认，并按确定性规则执行。
- 所有金额、客户、流水和凭证均为构造数据，不得用于真实财务决策。

## 测试与冒烟

```bash
./scripts/test.sh
python3 scripts/smoke_check.py
```

浏览器冒烟脚本需要当前环境已经安装 Playwright；项目依赖中不自动安装浏览器。

## 课堂材料

- `DEMO_RUNBOOK.md`：建议顺序、停顿点和现场兜底
- `demo_assets/scenarios/`：每个场景的课堂要点
- `demo_assets/speaker_notes/`：讲师手卡
- `demo_assets/screenshots/SCREENSHOT_PLAN.md`：截图范围与命名
- `demo_assets/recording/RECORDING_PLAN.md`：录屏准备与降级方案

## 已知限制

- 页面只模拟业务状态，不连接真实模型、知识库、银行或财务系统。
- 截图和完整视频本轮只准备清单，没有伪造已采集素材。
- 财务规则只覆盖课程需要的最小判断，不代表完整会计准则。
- 当前共享组件只在本项目内部使用，不抽取到仓库根目录。

