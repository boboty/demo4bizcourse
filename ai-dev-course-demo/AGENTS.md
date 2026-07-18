# 项目规则

## 技术栈

- Python 3.11+
- FastAPI、Pydantic
- pytest、httpx
- openpyxl
- 内存数据仓库；不依赖外部 API、云服务或数据库

## 目录职责

- `app/api/`：HTTP 路由和参数/响应转换，不承载业务查询规则。
- `app/models/`：Pydantic 领域模型和接口响应模型。
- `app/repositories/`：用户数据读取与筛选。
- `app/services/`：分页、导出等业务编排。
- `app/utils/`：无业务状态的通用工具。
- `tests/`：单元测试和接口测试。
- `demo_assets/`：课堂输入、执行记录和兜底材料，不参与运行时逻辑。

## 课堂演示状态页（/demo）

- `app/api/demo.py`、`app/services/demo_export_service.py` 是"课堂演示状态工程化"专用的教学接口
  （`/api/demo/users/export/null-failure`、`/api/demo/users/export/page-only`），只服务
  `app/static/demo_users.html` 的教学状态页，不得被正式代码路径引用。
- 正式导出接口 `app/api/users.py` + `app/services/user_export_service.py` 是唯一的业务真相；
  教学接口可复用其行格式/表头常量，但不得反向依赖教学模块，也不得让教学故障影响正式接口。
- `app/static/demo_nav.html`（`/demo`）与 `app/static/demo_users.html`（`/demo/users/<state>`，
  state ∈ base/null-failure/page-only/final）共用一份代码和一个 FastAPI 服务；状态由
  `app/main.py` 的受控路由白名单决定，未知 state 返回 404，不接受任意 query 注入。
- 新增或调整教学状态时：故障逻辑只允许出现在 `app/api/demo.py` /
  `app/services/demo_export_service.py` 中，讲师说明六部分内容随状态一起维护在
  `demo_users.html` 的 `DEMO_STATES` 配置里，不要复制出四份 HTML。

## Demo 2（/demo/codex-loop）

- `app/static/demo_codex_loop.html`（`/demo/codex-loop`）是纯前端模拟页面：不调用任何模型
  接口，不发出网络请求，不修改项目文件；八个节点的文案、角色、顺序和固定延迟
  （`STAGE_DELAYS_MS`，逐项 10~60 秒）都写在页面内的 `STAGES` 配置里，新增/调整节点时只改这份
  配置，不要引入随机延迟或随机失败。
- 流程建模为"主代理调度 + 代码子代理执行 + 轻量驳回 + 门禁放行"：`STAGES` 每项标注
  `role`（`main`/`sub`/`final`）与 `status`（READING/PLANNING/DELEGATED/SUBMITTED/
  GATE REJECTED/FIXING · VERIFYING/GATE PASSED/FINAL PASS），驱动角色着色和页面右上角
  的"当前状态"徽标。节点05 的门禁驳回是**唯一**一次轻量驳回，原因固定为"验证证据不足"，
  不是代码错误——新增内容时不要再引入空值 Bug、多轮驳回或人工确认弹窗。
- 该页面与 Demo 1 完全独立（不复用 `DEMO_STATES`/`demo_users.html`），但共用同一个讲师说明
  显示偏好（`sessionStorage["ai-demo.instructorNotes"]`）和导航页 `app/static/demo_nav.html`。
- `demo_nav.html` 中 Demo 1 的四张状态卡片使用 `.card`/`.card-enter` 类名，Demo 2 的入口卡使用
  单独的 `.codex-card`/`.codex-enter` 类名——这是刻意的隔离，避免选择器混淆导致断言/自动化
  误判入口数量，调整导航页时不要合并这两套类名。

## 代码与变更规则

- 遵循现有类型标注、命名和分层方式，保持实现简单直接。
- 用户列表的新增能力必须复用 `UserService.search_users` 的既有筛选逻辑，不得另写一套查询口径。
- 不得引入新的第三方依赖；`requirements.txt` 是依赖基线。
- 不得修改与当前任务无关的模块、公共行为或构建方式。
- 高风险、破坏性或存在多种业务解释的修改，实施前先说明影响和选择。

## 测试命令

```bash
./scripts/test.sh
```

## 完成定义

- 需求中的正常、空值、空集合和数量边界均有自动化测试。
- 相关测试和全量测试均通过。
- 接口行为、错误行为和变更范围与任务包一致。
- 未新增依赖、未修改无关文件、没有调试代码或临时文件。
- 只有在全量测试通过后才能宣布完成。

