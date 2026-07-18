# AI 研发课程双 Demo 项目

这是《外部企业人工智能赋能研发》课程使用的本地 FastAPI 演示项目。两个课堂 Demo 共用同一套代码、任务包和验收标准。

最终状态包含用户列表分页、筛选和 Excel 导出；`demo-baseline` 检查点保留导出实现前的项目状态，供现场从同一份任务包开始演示。

## 快速开始

```bash
./scripts/setup.sh
./scripts/run.sh
./scripts/test.sh
```

`setup.sh` 可重复执行：已有有效的 Python 3.11+ `.venv` 时会复用并重新核对依赖，缺失或不兼容时才重建。

服务默认监听 `http://127.0.0.1:8000`，OpenAPI 页面为 `http://127.0.0.1:8000/docs`。

## 已有接口

```text
GET /health
GET /api/users?page=1&page_size=20&username=ali&status=active
GET /api/users/export?username=ali&status=active
```

列表响应中的 `total` 是筛选后的总数，`items` 是当前页数据。用户名筛选不区分大小写并采用包含匹配，状态采用精确匹配。

导出接口复用同一筛选入口，返回列名为“用户ID、用户名、显示名称、邮箱、状态、创建时间”的 xlsx 文件。匹配结果超过 10000 行时返回 HTTP 422，不静默截断。

## 课堂资产

- Demo 1：`demo_assets/demo1/`
- Demo 2 单次现场输入：`demo_assets/demo2/01_live_prompt.md`
- 七节点讲解材料：`demo_assets/demo2/nodes/`
- 真实预跑日志：`demo_assets/demo2/logs/`
- Git 检查点说明：`DEMO_CHECKPOINTS.md`
- 完整运行手册：`DEMO_RUNBOOK.md`

## 课堂 Demo 页面

终端 A（准备与启动）：

```bash
./scripts/setup.sh
./scripts/run.sh
```

终端 B（测试）：

```bash
./scripts/test.sh
```

- 页面地址：`http://127.0.0.1:8000/demo/users`（单文件静态页 `app/static/demo_users.html`，无外部 CDN，离线可用）
- 页面复用列表接口：`GET /api/users?page=&page_size=&username=&status=`，页面默认每页 8 条
- 导出功能：已连接现有 `GET /api/users/export`，按当前用户名/状态筛选导出全部匹配结果（不受分页限制）
- 演示数据：应用启动时由 `InMemoryUserRepository.with_sample_data()` 在内存中幂等构建 23 条用户（含 active/inactive/pending 与空显示名边界），每页 8 条时默认数据 3 页、active 筛选 2 页；不影响测试
- 浏览器冒烟验收（可选，需系统 Python 已装 Playwright）：`python3 scripts/demo_smoke_check.py`

最小课堂操作步骤：

1. 打开页面，确认无筛选时显示 8 条、共 3 页；
2. 输入用户名（如 `chen`）或选择状态（如 `active`）后点“查询”，观察筛选摘要与分页回到第一页；
3. 点“重置”恢复默认条件；
4. 点“导出 Excel”，观察下载的 `users.xlsx` 与当前筛选一致；
5. 展开页面底部“请求详情”，对照页面与 API 请求/响应。

## 演示重置

```bash
./scripts/reset_demo.sh
```

该命令会丢弃本 Demo 的 tracked 修改，清理 `app/`、`tests/`、`scripts/` 下的未跟踪实现文件，切到干净的 `demo-baseline` 并保留 `.venv` 与其他目录下的讲师笔记。任务包和现场输入已包含在 baseline 中；最终讲解资产可通过 `./scripts/restore_final.sh` 恢复。执行前应保存需要保留的代码修改。

恢复脚本只执行安全的 `git switch main`，不会丢弃或清理本地修改。
