# DECISIONS

> 记录"为什么这么做"，只在做出会影响后续开发的工程决策时追加一条，不是任务日志，也不是逐次修改记录。

## D-001：筛选放在 service 层，且在权限过滤之后、分页之前

- 背景：`CODING-STANDARDS.md` 要求筛选进入既有 `app/financing/service.py`，且不能扩大 `repository.py` 已经建立的 tenant 权限范围。
- 决策：`customer_name`（以及后续的 `status`）筛选在 `all_applications_for_user()` 返回结果之后、`paginate()` 之前进行，不放在 repository 层，也不放在 API 层。
- 影响：分页的 `total` 永远反映"筛选后、权限内"的数量；后续加状态筛选、导出都应遵守同一顺序——权限 → 筛选 → 分页/导出。

## D-002：客户名称筛选用大小写不敏感的子串匹配，不引入新依赖

- 背景：任务要求"客户名称为模糊筛选"，但没有给出大小写、全半角等细节；`CODING-STANDARDS.md` 禁止引入新的第三方依赖。
- 决策：用 `str.lower()` 做子串包含判断（`needle in row["customer_name"].lower()`），不引入第三方模糊匹配/分词库。
- 影响：如果未来验收标准要求更复杂的模糊逻辑（拼音、编辑距离等），需要重新评估；目前先满足"子串包含"这一最小可验证语义。

## D-003：类型注解统一用 `typing.Optional`，不使用 `X | None`

- 背景：本机裸 `python3` 是系统自带的 3.9，仓库共享 `.venv` 才是 3.12；两者都可能被用来跑测试，而 PEP 604 的 `X | None` 联合类型语法只有 3.10+ 支持，混用会在导入期直接报错。
- 决策：本项目的可选参数一律用 `typing.Optional[...]`，不使用 PEP 604 的 `|` 写法；`verify.sh` 优先使用仓库共享 `.venv`，找不到时才退回系统 `python3`。
- 影响：后续新增字段（例如 `status` 筛选）时延续同一写法，避免同一个环境问题重复出现。

## D-004：客户名称筛选的"完成"包含页面入口，不止 API

- 背景：`static/index.html` 是这个功能目前唯一的用户入口（没有其它前端）；只实现 `service`/API 但不接到页面上，用户实际上还是用不了这个功能。
- 决策：在 `static/index.html` 原有的列表 + 分页基础上，加一个客户名称输入框和筛选/清除按钮，点击后把输入值作为 `customer_name` 查询参数真实传给 `/api/financing-applications`；翻页时沿用当前的筛选值（不清空），切换筛选条件或清除时把页码重置为第 1 页。没有引入新的前端依赖，用的是原页面已有的原生 `fetch` + DOM 操作风格。
- 影响：后续的状态筛选、导出也要遵循同一标准——"完成"=对应的 service/API 行为 + 页面里用户能实际点到的入口（见 `TASK.md`《功能完成定义》），具体页面实现方式不做规定，由实现者自行决定。

## D-005：状态筛选按 `data.json` 中出现的既有取值做精确匹配

- 背景：没有找到集中定义的状态枚举来源，只能从 `app/financing/data.json` 的样例反推（`SUBMITTED` / `APPROVED` / `FUNDED` / `REJECTED`）。
- 决策：不新建枚举类型或校验白名单，直接对 `row["status"]` 做精确字符串匹配；不存在的取值自然返回空结果，不报错。
- 影响：如果未来引入新的状态值或状态机校验，这里的精确匹配逻辑不需要改动，但枚举来源应尽快集中定义。

## D-006：导出 payload 固定 `id`/`customer_name`/`status`/`amount` 四个字段，并携带筛选条件与权限范围

- 背景：`PROJECT-MEMORY.md`/既有代码没有约定导出字段和 payload 结构；任务要求导出必须是"当前筛选结果"并保留权限范围。
- 决策：`export_applications()` 复用 `_filtered_rows()`（与列表接口相同的权限 → 筛选顺序，见 D-001），不分页，输出 `EXPORT_FIELDS = (id, customer_name, status, amount)`；payload 额外记录 `filters`（本次筛选条件）、`requested_by`（发起用户）、`tenant_scope`（该用户当时的 tenant 权限范围）。
- 影响：后续如果要扩展导出格式（如 CSV/Excel），应在已有 `rows` 数据基础上做序列化，不要绕开 `_filtered_rows()` 重新拼权限逻辑。

## D-007：状态筛选用下拉框枚举已知取值，并与客户名称筛选共用同一次查询

- 背景：D-005 已经确定状态是精确匹配且取值来自 `data.json` 的既有样例；页面上如果用自由文本框容易输错、测不出"精确匹配"这个语义。
- 决策：`static/index.html` 加一个 `<select>`，选项为 `SUBMITTED`/`APPROVED`/`FUNDED`/`REJECTED` 加一个"全部状态"空选项；客户名称输入框和状态下拉框共用同一个"筛选"按钮和同一次 `load()` 调用，两个条件都以 `URLSearchParams` 的形式附加到 `/api/financing-applications`，没有值的条件不附加，从而同时支持单条件和组合筛选。
- 影响：如果后续状态枚举来源变化（例如改为从后端接口获取取值列表），只需要替换 `<select>` 的选项来源，不需要改查询拼接逻辑。

## D-008：导出按钮复用当前筛选条件，并把真实的后端返回结果渲染到页面上

- 背景：任务要求导出"导出的必须是当前筛选条件下的结果"，且页面不能用假按钮糊弄过去。
- 决策：导出按钮点击时，把当前页面上的 `customer_name`/`status` 筛选值（与列表查询完全相同的两个变量）作为 query 参数 POST 到 `/api/financing-applications/export`；拿到响应后直接把返回的 `job.id`、`job.status`、`job.payload.filters` 和导出行数渲染进页面上一个结果区域，不单独维护一份"导出成功"的前端文案。
- 影响：导出结果区域显示的永远是后端 `ExportQueue` 的真实返回值；如果后端行为变化（例如 payload 结构调整），页面展示会直接反映出来，不需要额外同步两处状态。
