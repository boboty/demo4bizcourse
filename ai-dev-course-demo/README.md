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

访问根路径 `http://127.0.0.1:8000/` 会自动重定向到课堂演示导航页 `/demo`，课堂现场无需手动敲 `/demo` 地址。

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

- 演示导航页：`http://127.0.0.1:8000/demo`（清楚区分 Demo 1 与 Demo 2 两个演示区域）

所有页面共用一个代码版本和一个 FastAPI 服务；教学故障被隔离在 Demo 专用页面和接口中，
正式用户导出接口 `GET /api/users/export` 始终保持正确，不受任何教学状态影响。

### Demo 1 · 从模糊需求到可验证任务

四个教学状态页（导航页点击进入，也可直接访问）：

```text
/demo/users/base           00 · Baseline               需求尚未实现
/demo/users/null-failure   01 · One-line Implementation 功能出现，但边界失败
/demo/users/page-only      02 · Tests Green, Goal Missed 测试通过，但原始目标未达
/demo/users/final          03 · Final Pass              目标、边界与证据闭环
```

旧地址 `/demo/users` 保留，重定向到 `/demo/users/final`。

四个页面是基于真实开发与验收问题压缩整理的教学状态。它们共用一个代码版本和一个服务
（单文件静态页 `app/static/demo_users.html` + `app/static/demo_nav.html`，无外部 CDN，离线可用）。
教学故障被隔离在 Demo 专用页面和接口中（`app/api/demo.py`、`app/services/demo_export_service.py`，
对应 `/api/demo/users/export/null-failure`、`/api/demo/users/export/page-only`）。

- 页面复用列表接口：`GET /api/users?page=&page_size=&username=&status=`，页面默认每页 8 条
- Final 状态导出：连接正式 `GET /api/users/export`，按当前用户名/状态筛选导出全部匹配结果（不受分页限制）
- 演示数据：应用启动时由 `InMemoryUserRepository.with_sample_data()` 在内存中幂等构建 23 条用户（含 active/inactive/pending、`bob` 等空显示名边界），每页 8 条时默认数据 3 页、active 筛选 2 页；不影响测试
- 每个状态页顶部有状态标识、返回导航、上一个/下一个状态按钮；“显示讲师说明/隐藏讲师说明”偏好存于 `sessionStorage`，跨状态页保留，不进后端

最小课堂操作步骤：

1. 打开 `/demo`，按 00 → 01 → 02 → 03 顺序点击“进入演示”；
2. 00 Base：点击“导出 Excel”，确认只提示“功能待实现”，不产生任何导出请求；
3. 01 Null Failure：默认条件导出成功；筛选用户名 `bob` 后再次导出，确认稳定失败且提示可解释；
4. 02 Page Only：确认页面显示“共 23 条”，导出后打开文件确认只有当前页 8 条，展开请求详情核对 `page`/`page_size`；
5. 03 Final：默认导出 23 条；筛选（如 `chen` + `active`）后导出，确认导出与筛选一致且请求不含分页参数；
6. 任意状态页可用“上一个状态 / 下一个状态”切换，或点击“显示讲师说明”查看六部分教学内容。

### Demo 2 · 完整任务包驱动研发闭环

```text
/demo/codex-loop
```

同一个导出任务，这次一次性交给研发智能体一份完整任务包（目标、功能要求、技术约束、验收标准、
验证要求），观察其在浏览器中模拟完成读取项目 → 制定计划 → 修改代码 → 生成测试 → 运行验证 →
独立验收 → 输出证据的执行闭环。**本页只在浏览器中模拟展示，不调用任何大模型接口，不发出网络
请求，不修改项目文件**；七个阶段的内容、顺序和固定延迟（0.6~1.2 秒）全部写死在
`app/static/demo_codex_loop.html` 中，可稳定重复演示。

- 控制：提交任务包并开始执行 / 暂停 / 继续 / 单步执行 / 直接查看最终结果 / 重新演示（页面刷新也会恢复到未运行状态）
- 最终“完成与证据映射”展示验收标准 10/10 覆盖情况，并与 Demo 1 的九步弯路做一页对照
- 讲师说明与其他 Demo 页面共用同一个 `sessionStorage` 偏好（`ai-demo.instructorNotes`）

最小课堂操作步骤：

1. 展示左侧完整任务包，强调目标、边界和验收标准；
2. 点击“提交任务包并开始执行”，在“02 · 制定计划”阶段停顿，指出实现计划与验证计划同时产生；
3. “05 · 运行自动化测试”通过时指出：这次没有经历 Demo 1 的两轮需求遗漏；
4. “06 · 真实场景验证”阶段强调：自动化测试通过后仍需真实浏览器证明原始目标；
5. 展示“07 · 完成与证据映射”的 10/10 验收覆盖；
6. 滚动到页面底部的 Demo 1 / Demo 2 对照区收尾。

### 课前检查与冒烟验收

```bash
PYTHONDONTWRITEBYTECODE=1 ./scripts/test.sh -p no:cacheprovider
PYTHONDONTWRITEBYTECODE=1 python3 -u scripts/demo_smoke_check.py
```

教学状态检查脚本（可选）：

```bash
python3 scripts/demo_stage_checks.py page-only   # Stage 2 局部检查（故意不覆盖完整验收）
python3 scripts/demo_stage_checks.py final       # Final 完整验证
```

浏览器冒烟验收（可选，需系统 Python 已装 Playwright）：

- `python3 scripts/demo_smoke_check.py`：Final 状态页面真实操作链路
- `python3 scripts/demo_stage_smoke_check.py`：导航页（含 Demo 1/Demo 2 区分）+ 四状态页完整回归
- `python3 scripts/demo_codex_loop_smoke_check.py`：Demo 2 播放控制、七阶段固定顺序、10/10 验收覆盖、无网络请求、与正式接口/原四状态页无回归

## 演示重置

```bash
./scripts/reset_demo.sh
```

该命令会丢弃本 Demo 的 tracked 修改，清理 `app/`、`tests/`、`scripts/` 下的未跟踪实现文件，切到干净的 `demo-baseline` 并保留 `.venv` 与其他目录下的讲师笔记。任务包和现场输入已包含在 baseline 中；最终讲解资产可通过 `./scripts/restore_final.sh` 恢复。执行前应保存需要保留的代码修改。

恢复脚本只执行安全的 `git switch main`，不会丢弃或清理本地修改。
