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

同一个导出任务，这次由**主代理**读取完整任务包（目标、功能要求、技术约束、验收标准、验证要求）
并制定计划，拉起**代码子代理**执行；子代理提交实现与验证证据后，主代理执行阶段门禁——因“全量
验证证据不足”驳回一次（不是代码错误），子代理补充全量验证后主代理放行，最终由**独立验收代理**
重新对照任务包给出 PASS。**本页只在浏览器中模拟展示，不调用任何大模型接口，不发出网络请求，
不修改项目文件**；八个节点的内容、角色、顺序和固定延迟（10~60 秒/节点）全部写死在
`app/static/demo_codex_loop.html` 中，可稳定重复演示。

八个节点：

```text
01 主代理读取任务包        READING
02 主代理制定执行计划      PLANNING
03 主代理拉起代码子代理    DELEGATED
04 代码子代理完成实现      SUBMITTED（只运行新增测试，刻意保留“未运行全量回归测试”的轻量缺口）
05 主代理执行阶段门禁并驳回 GATE REJECTED（原因：验证证据不足，不是代码错误）
06 代码子代理补充验证      FIXING / VERIFYING（全量 pytest 25 passed，第一次即通过）
07 主代理门禁放行          GATE PASSED
08 独立验收代理最终验收    FINAL PASS（9 项验收核对）
```

- 三个角色用图标/颜色区分：🧭 主代理（蓝）、🛠 代码子代理（绿）、✅ 独立验收代理（紫）；
  页面顶部有角色图例和“角色协作流程”静态图，右上角“当前状态”徽标随节点推进实时更新
- 控制：提交任务包并开始执行 / 暂停 / 继续 / 单步执行 / 直接查看最终结果 / 重新演示（页面刷新也会恢复到未运行状态）
- 最终“完成与证据映射”展示验收项 9/9 覆盖情况、门禁历史（REJECTED → PASSED），并保留四条观点钉子
  与主结论：**丝滑不是一路不停，而是任务定义清楚、分工明确、门禁有效，只在必要位置做一次低成本驳回**
- 讲师说明与其他 Demo 页面共用同一个 `sessionStorage` 偏好（`ai-demo.instructorNotes`）

最小课堂操作步骤：

1. 展示左侧完整任务包与角色协作流程图，强调目标、边界和验收标准；
2. 点击“提交任务包并开始执行”，在“02·主代理制定执行计划”停顿，指出主代理拥有计划权和调度权；
3. “03·主代理拉起代码子代理”强调：完整任务包被拆解为边界清楚的子任务；
4. “05·主代理执行阶段门禁并驳回”重点停顿，强调驳回的是证据、不是代码错误；
5. “06·代码子代理补充验证”展示全量测试 25 passed；“07·主代理门禁放行”强调放行依据；
6. “08·独立验收代理最终验收”展示 PASS 与 9 项验收证据；
7. 收尾展示四条观点钉子与主结论，滚动到页面底部的 Demo 1 / Demo 2 对照区。

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
- `python3 scripts/demo_codex_loop_smoke_check.py`：Demo 2 播放控制、八节点固定顺序与角色标注、
  门禁驳回（REJECTED）与放行（PASSED）、9/9 验收覆盖、无网络请求、与正式接口/原四状态页无回归

## 演示重置

```bash
./scripts/reset_demo.sh
```

该命令会丢弃本 Demo 的 tracked 修改，清理 `app/`、`tests/`、`scripts/` 下的未跟踪实现文件，切到干净的 `demo-baseline` 并保留 `.venv` 与其他目录下的讲师笔记。任务包和现场输入已包含在 baseline 中；最终讲解资产可通过 `./scripts/restore_final.sh` 恢复。执行前应保存需要保留的代码修改。

恢复脚本只执行安全的 `git switch main`，不会丢弃或清理本地修改。
