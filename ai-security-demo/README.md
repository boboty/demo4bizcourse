# 人工智能安全保障能力提升 · 课程 Demo

本轮交付 **Demo B：提示词注入与智能体越权**。其他 A / C / D 尚未开发。某产业集团、采购单、供应商、身份与账户均为虚构，模型为**离线确定性模拟器**，不连接真实企业系统或外部 AI API。

## 安装、运行与复演

需要 Python 3.12+ 与 uv。首次安装需要网络；课前完成安装，之后运行、测试和全部页面均可断网。

```bash
cd ai-security-demo
make setup
make dev
```

浏览器打开 [http://127.0.0.1:8016/demo/b](http://127.0.0.1:8016/demo/b)。只监听回环地址；使用单个 Uvicorn 进程，不加 `--workers`。内存状态用于单机课堂，重启恢复初始状态，不用于多人生产部署。关闭启动终端或按 Ctrl+C 停止。

点击“1 正常只读查询” → “2 注入污染文档” → “故障注入：执行当前提案” → “安全模式：执行相同提案”。也可“一键完整复演”，自动先重置，再依次执行正常与污染对比。任何时候可“重置全部状态”，清空运行与审计，恢复两套待审批状态；旧运行标识立即失效。

[Demo B 讲师操作剧本](DEMO_B_RUNBOOK.md) 包含逐步操作、预期结果、停顿点和故障备用路径。

## 真实业务链与权限边界

`app/main.py`：后端检索固定采购资料，按开关注入不可信正文，模拟器解析正文的工具 JSON 形成提案。正常文档产生 `purchase.read`；污染产生 `purchase.approve`。两种模式提交**同一运行的同一提案**，两个隔离的内存采购单可比较。

- 固定可信身份 `buyer-017 / procurement_reader`，客户端不能指定或覆盖角色。
- `authorize()` 按角色、对象和动作默认拒绝，只允许读取 `PO-2026-017`。
- 安全模式真实调用授权函数，越权返回 HTTP 403 / `DENY`，保留前后快照且不写业务状态。
- 故障模式明确跳过权限判断，实际将**隔离的虚构采购单**从“待审批”改为“已批准”，标记 `BYPASS`。即使在故障模式，仍仅接受原运行提案、唯一虚构对象和白名单工具参数，不提供任意执行器。
- 每次执行记录固定身份、角色、对象、动作、授权结果、policy_allowed、运行 ID、请求 ID 与业务快照。重复执行可观察，模拟“批准”写操作本身幂等，每次仍追加审计。
- 未做登录或生产安全平台；固定身份用于清楚展示模型与授权边界。故障入口仅作本地课堂实验。

## 验证

```bash
make check                    # Ruff + Pyright + pytest，离线
uv run --offline python scripts/http_smoke.py  # 先启动服务；真实 HTTP，最后恢复初始状态
python3 scripts/fingerprint.py # 整个仓库相对基线、含非忽略 untracked 的 SHA-256
```

浏览器自检使用已安装的 Playwright 环境，无需作为运行依赖。证据放本目录 `evidence/`（Git 忽略，不参与交付指纹），详见交付报告。业务检查覆盖正常只读、实际污染提案、故障写入、安全拒绝、伪造角色/对象/动作/参数、拒绝无副作用、重复执行与重置。指纹脚本包含删除状态、路径、可执行位与文件内容，带长度前缀，排除 Git 忽略产物；不依赖暂存状态。

## 工程依据与明确例外

治理：Agent Board v0.2.3 工单 #1 记录执行、交付、独立验证；不作为质量规范。质量：BenYan Engineering Standard v2.0.0，权威快照 `9edd0b656dadf3c264d6f808f4f16f24a69b2684`，负责 API、错误、请求标识、测试和界面标准。

沿用仓库现有 FastAPI + 原生 HTML/CSS/JavaScript 工程习惯。按用户离线轻量要求，明确偏离通用 React/Vite/Compose/PostgreSQL 默认值：单页控制台没有前端构建、路由框架、持久化或数据库需求，不引入 Docker、数据库、外部服务；FastAPI 同源提供 `/api/v1` 和静态页面。

页面实际引用本地 `app/static/design-system/styles.css` 及上游 tokens 快照。唯一离线改动为 `tokens/fonts.css` 移除 Google Fonts 网络 import，使用上游 typography 的系统字体回退。上游 `Button.jsx` / `Card.jsx` 原样保留作设计依据，`app.css` 将其视觉规则适配为原生按钮和卡片，使用官方色彩、字体、间距、圆角和阴影变量。无需引入 React 运行时，不加载 CDN、在线字体或图标。

当前是 Worker 交付，独立 Verifier 与 Human 验收分别记录在 Board；不得将自检结果表述为 Human 已接受。未提交、推送或合并代码。
