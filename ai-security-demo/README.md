# 人工智能安全保障能力提升 · 课程 Demo

本应用包含 **Demo A：敏感数据识别、授权与脱敏**、**Demo B：提示词注入与智能体越权**、**Demo C：AI 使用合规审计与人工认定** 和 **Demo D：合成账号/API 日志分析与人工核查**。独立验收与 Human 裁决以 Agent Board 事实为准；A/C/D 尚未 Human 接受，B 已 Human 接受。某产业集团、平台日志、制度、身份、合同、采购单、供应商与账户均为虚构；规则及辅助识别均为离线确定性教学模拟，不连接真实企业系统或外部 AI API。

## 安装、运行与复演

需要 Python 3.12+ 与 uv。首次安装需要网络；课前完成安装，之后运行、测试和全部页面均可断网。

```bash
cd ai-security-demo
make setup
make dev
```

浏览器打开 [Demo A](http://127.0.0.1:8016/demo/a)、[Demo B](http://127.0.0.1:8016/demo/b)、[Demo C](http://127.0.0.1:8016/demo/c) 或 [Demo D](http://127.0.0.1:8016/demo/d)。课程页可互相切换。只监听回环地址；使用单个 Uvicorn 进程，不加 `--workers`。内存状态用于单机课堂，重启恢复初始状态，不用于多人生产部署。关闭启动终端或按 Ctrl+C 停止。

四个 Demo 的独立讲师剧本分别为 [A](DEMO_A_RUNBOOK.md)、[B](DEMO_B_RUNBOOK.md)、[C](DEMO_C_RUNBOOK.md) 和 [D](DEMO_D_RUNBOOK.md)；统一彩排顺序、时间建议和备用方式见 [四 Demo 彩排剧本](DEMO_REHEARSAL.md)。定稿课件 62 页的稳定 slide ID、标题、讲师动作和 Demo 对应见 [逐页映射](DEMO_COURSE_MAPPING.md)；现场速查见[课堂手卡](CLASSROOM_CUE_CARDS.md)，离线运行与故障处理见[环境检查清单](CLASSROOM_ENV_CHECKLIST.md)；抽取脚本为 `scripts/extract_course_notes.py`，原始讲师 notes 及来源校验保存在忽略目录 `evidence/course-source/notes.json`。

Demo A 当前课堂主线：运行规则识别 → 查看辅助识别 → 确认人工修正 → 申请脱敏预览 → 人工确认并完成脱敏。固定模拟将一般合同金额误报为个人信息；修正不创建权限，未经授权资料仍被后端拒绝，涉密资料不进入普通识别、脱敏或上传链。

Demo B 对课件第 30 页有明确课堂适配：固定只读身份代替登录流程，读取与审批两类工具动作替代完整四工具清单，读取后的采购状态用于摘要对照。该适配和逐字差异已在 B 讲师剧本说明；B 核心实现保持已接受版本。

Demo C 主线为建立案例、查看规则线索、生成辅助解释、核对原始证据并提交人工认定；可导出候选问题清单。Demo D 主线为汇总日志、聚合异常、辅助研判、人工核查并生成四栏简报。各 Demo 独立重置。

四 Demo 的真实页面步骤、课堂时间和复位方式见[彩排剧本](DEMO_REHEARSAL.md)及各自 runbook。

Demo B 使用单一动态“下一步”按钮：依次显示“运行正常查询”→“检索污染文档”→“故障模式：执行越权提案”→“安全模式：执行同一提案”。顶部“重置演示”清空本轮状态。课堂适配说明见 B runbook。

### Demo A：识别、授权与脱敏

固定虚构采购合同由确定性字段规则识别，结果展示字段证据、位置及分类依据。后端按固定身份和资料目录策略分别允许或拒绝处理。脱敏使用真实服务端字符串遮盖，普通业务字段保留；识别结果不能创建权限，脱敏不保证匿名化。

独立涉密示例只提供固定标识、分类标签和禁止边界，正文不随静态资源分发。后端识别、脱敏和上传入口均在普通逻辑前拒绝，并只在审计中保存资料标识、动作、拒绝策略和请求 ID。A 的运行、审计与重置均独立于 B。

### Demo B：提示词注入与智能体越权（已接受）

课堂按钮按阶段动态显示：运行正常查询 → 检索污染文档 → 故障模式：执行越权提案 → 安全模式：执行同一提案。顶部“重置演示”清空本轮运行与审计，恢复两套待审批状态。

## Demo B 真实业务链与权限边界

`app/main.py`：后端检索固定采购资料，按开关注入不可信正文，模拟器解析正文的工具 JSON 形成提案。正常文档产生 `purchase.read`；污染产生 `purchase.approve`。两种模式提交**同一运行的同一提案**，两个隔离的内存采购单可比较。

- 固定可信身份 `buyer-017 / procurement_reader`，客户端不能指定或覆盖角色。
- `authorize()` 按角色、对象和动作默认拒绝，只允许读取 `PO-2026-017`。
- 安全模式真实调用授权函数，越权返回 HTTP 403 / `DENY`，保留前后快照且不写业务状态。
- 故障模式明确跳过权限判断，实际将**隔离的虚构采购单**从“待审批”改为“已批准”，标记 `BYPASS`。即使在故障模式，仍仅接受原运行提案、唯一虚构对象和白名单工具参数，不提供任意执行器。
- 每次执行记录固定身份、角色、对象、动作、授权结果、policy_allowed、运行 ID、请求 ID 与业务快照。重复执行可观察，模拟“批准”写操作本身幂等，每次仍追加审计。
- 未做登录或生产安全平台；固定身份用于清楚展示模型与授权边界。故障入口仅作本地课堂实验。

## Demo C：AI 使用合规审计与人工认定

`app/demo_c.py` 提供三组虚构调用日志、制度原文、稳定 ID `LIST-AI-TOOL-01` 的工具准入白名单及原始证据。后端按调用元数据运行确定性规则，覆盖未准入工具、潜在敏感输入与脱敏元数据、访问方式、审批和留存；每条命中携带证据链接及日志字段作为依据。离线模拟解释卡关联事件、制度条款、证据 ID 和待核实事项，`final_decision` 固定为空。候选问题清单通过 `/api/v1/c/runs/{run_id}/candidate-questions` 生成并由页面导出为 JSON。

课堂流程为建立案例 → 查看规则线索 → 生成辅助解释 → 核对原始证据 → 人工认定。认定由固定演示身份 `audit-024 / ai_compliance_reviewer` 执行，必须引用本次已核对证据并填写理由；关键日志字段缺失时可判“证据不足”。审计记录动作、对象、结果、固定身份、运行和请求 ID。C 的运行和重置与 A/B 分离；本地模拟解释器不能写入最终认定。

## 验证

```bash
make check                    # Ruff + Pyright + pytest，离线
uv run --offline python scripts/http_smoke_a.py # 已启动服务；真实 HTTP 覆盖 A，恢复 A/B 初态
uv run --offline python scripts/http_smoke.py  # 先启动服务；真实 HTTP，最后恢复初始状态
uv run --offline python scripts/http_smoke_c.py # 先启动服务；真实 HTTP 覆盖 C 并核对 A/B 隔离
uv run --offline python scripts/http_smoke_d.py # 先启动服务；真实 HTTP 覆盖 D 及 A/B/C 状态隔离
node scripts/browser_e2e_d.cjs # Chrome 本地完整流程与外网请求拦截
uv run --offline python scripts/http_smoke_integrated.py # A/B/C/D 课堂 HTTP 链与各自隔离重置
node scripts/browser_e2e_integrated.cjs # Chrome A→B→C→D、外网拦截、故障恢复及下载
python3 scripts/fingerprint.py # 整个仓库相对基线、含非忽略 untracked 的 SHA-256
```

Demo A 有独立自动测试与真实 HTTP smoke。完整集成指纹通过 `scripts/fingerprint.py --baseline f231501646f1141891b3213284dc5a80cac21104` 计算，包含累计 tracked diff 与非忽略 untracked 文件。

浏览器脚本使用已安装的 Playwright 环境，无需作为运行依赖；C、D 的专项脚本和最终 `browser_e2e_integrated.cjs` 都会拦截外网请求。原始运行结果、截图和下载文件存于忽略目录 `evidence/integration-worker/`，不参与交付指纹。A 测试覆盖服务端授权、涉密前置拒绝、人工证据修正和下一步确认边界；C/D 保留既有独立测试。指纹脚本计算路径、可执行位与文件内容，排除 Git 忽略产物，不依赖暂存状态。无现场录屏；验收证据是可重复脚本、HTTP/浏览器结果和截图，不称作录屏。

## 工程依据与明确例外

治理：Agent Board v0.2.3 工单 #1–#5 记录各阶段执行、交付、独立验证与 Human 裁决，以 Board 事实为准；不作为质量规范。质量：BenYan Engineering Standard v2.0.0，权威快照 `9edd0b656dadf3c264d6f808f4f16f24a69b2684`，负责 API、错误、请求标识、测试和界面标准。

沿用仓库现有 FastAPI + 原生 HTML/CSS/JavaScript 工程习惯。按用户离线轻量要求，明确偏离通用 React/Vite/Compose/PostgreSQL 默认值：单页控制台没有前端构建、路由框架、持久化或数据库需求，不引入 Docker、数据库、外部服务；FastAPI 同源提供 `/api/v1` 和静态页面。

页面实际引用本地 `app/static/design-system/styles.css` 及上游 tokens 快照。唯一离线改动为 `tokens/fonts.css` 移除 Google Fonts 网络 import，使用上游 typography 的系统字体回退。上游 `Button.jsx` / `Card.jsx` 原样保留作设计依据，`app.css` 将其视觉规则适配为原生按钮和卡片，使用官方色彩、字体、间距、圆角和阴影变量。无需引入 React 运行时，不加载 CDN、在线字体或图标。

Demo A/C/D 的独立 verdict 与 Human 裁决以 Agent Board 事实为准；截至当前 A/C/D 均尚未 Human 接受。B 的既有 Human 接受事实仅适用于其已接受基线，不代表 A/C/D 已接受。Worker 交付或自检结果不代表 Human 接受。
