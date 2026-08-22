# 讲师 Runbook｜4 讲 4 Demo

## 总原则

同一个 Git 仓库只用于保存资产；Demo 1 与 Demo 2 共用 `workspaces/demo12-financing/`，Demo 3、Demo 4 使用各自独立 workspace。每次演示都先执行 reset，再从指定目录新开 Luna + High。不要从 `ai-rd-system-demo/` 根目录启动课堂会话。

所有命令默认从 `ai-rd-system-demo/` 根目录执行；每个代码块中的 `cd` 都是课堂操作的一部分。

## 课前准备｜先确认环境，再开始 Demo

课堂统一使用仓库根目录的 `.venv`，Python 版本统一为 3.12。不要为各 workspace 创建独立虚拟环境，也不要污染系统 Python。

### 首次环境安装

```bash
cd ai-rd-system-demo
brew install python@3.12  # 已安装可跳过
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt
which python
python --version
which pytest
```

正常结果：`which python` 指向 `ai-rd-system-demo/.venv/bin/python`，版本为 Python 3.12，`which pytest` 指向 `.venv/bin/pytest`。如果命令指向系统路径，先停止，不要继续课堂操作。

### 虚拟环境确认

每次开新终端或重新进入课堂前都确认：

```bash
cd ai-rd-system-demo
source .venv/bin/activate
which python
python --version
which pytest
```

### 上课前 Preflight

```bash
cd ai-rd-system-demo
source .venv/bin/activate
which python
python --version
python scripts/acceptance_check.py
```

正常结果：所有 workspace、baseline、隔离检查和 Demo 3/4 确定性检查均为 `PASS`，最后显示 `OVERALL: PASS`。异常结果：立即停止课堂，先检查当前 shell 是否使用仓库根目录 `.venv`、旧服务是否占用端口，再重新运行；不要因为 import 失败临时 `pip install`，不要在课堂中访问 PyPI 修环境。

### Demo12 baseline 检查

```bash
./scripts/reset_demo1.sh
cd workspaces/demo12-financing
../../.venv/bin/python -m pytest -q
cd ../..
```

正常结果：baseline 测试通过。若 import 失败，首先检查是否使用 `ai-rd-system-demo/.venv`，不要切换到系统 Python。

### 查看 baseline 页面

```bash
cd workspaces/demo12-financing
../../.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

浏览器打开 <http://127.0.0.1:8000/>。正常结果：能看到融资申请基础列表；异常结果：停止服务并检查 `.venv`、端口和当前 workspace，不在课堂中临时访问 PyPI。

### 服务启动方式

Demo 3 developer 测试全绿后，在 developer workspace 的另一个终端启动固定端口黑盒服务：

```bash
cd workspaces/demo3-developer
./bin/start-blackbox
```

该脚本使用仓库根目录 `.venv`，服务地址为 `http://127.0.0.1:8765`。端口已被旧进程占用时，先停止旧服务，再重新启动。

## Demo 1 / Demo 2 共同基准

### 业务需求基准

融资申请列表需要支持客户名称和融资状态筛选，并支持导出。两次演示都从同一个未实现该需求的融资申请 baseline 开始。

### 独立质控 / 业务验收标准

标准公开，验收实现独立。讲师在退出 workspace 后运行同一套独立验收；开发 Agent 只运行开发侧 `../../.venv/bin/python -m pytest -q`，不读取验收脚本实现。

- 客户名称为模糊筛选，状态为精确筛选。
- 覆盖单条件、多条件和空结果。
- 保留既有数据权限，筛选和导出不能越权。
- 导出走已有异步任务通道，且导出当前筛选结果。
- 导出任务保留 `customer_name`、`status` 和当前用户权限范围。
- 导出字段严格为 `id`、`customer_name`、`status`、`amount`。
- 前端具备客户筛选、状态筛选和导出操作；只验收功能行为，不绑定 HTML `id`、`class` 或变量名。

### 实验控制变量

不变：同一个 workspace、同一个 baseline、同一个 `AGENTS.md`、同一个模型 Luna + High、同一套独立验收。

唯一变化：Demo 1 使用一句话 Direct Task；Demo 2 使用完整 Spec-driven Task。

## Demo 1｜demo12-financing｜一句话 Direct Task｜15 min

### 1A. CNN 可视化｜约 5 min

打开 Adam Harley CNN 3D 可视化：<https://adamharley.com/nn_vis/cnn/3d.html>。

收口：模型内部面对的往往不是一个答案，而是一组候选；业务系统最终必须落成一个判断。

### 1B. 从共用 workspace 启动 Codex｜约 10 min

```bash
./scripts/reset_demo1.sh
cd workspaces/demo12-financing
# 从这里新开 Luna + High
```

只粘贴下面这一句话，不补充边界、约束或验收条件：

> 给融资申请列表增加客户名称和融资状态筛选，并支持导出。

观察它是直接做还是追问；如果有改动，只展示 diff、追问和完成依据，不修复、不运行 Demo 2 的 Spec。

开发 Agent 只运行开发侧测试：

```bash
../../.venv/bin/python -m pytest -q
```

关闭会话并退出 workspace 后，由讲师从仓库根目录运行同一套独立验收，再保存 Demo 1 差异：

```bash
cd ../..
.venv/bin/python instructor/checks/task_a_acceptance.py
./scripts/capture_diff.sh demo1
```

## Demo 2｜demo12-financing｜完整 Spec-driven Task｜15 min + 学员 25 min

Demo 1 会话结束后，先恢复完全相同的 baseline；仍进入同一个 workspace，但必须新开 Luna + High 会话：

```bash
./scripts/reset_demo2.sh
cd workspaces/demo12-financing
# 关闭 Demo 1 会话，从这里新开 Luna + High
```

从本 Runbook 复制下面的完整 Spec，不读取 workspace 外的其他任务文件：

> # 任务 A｜五要素可交办任务
>
> ## 01 背景｜为什么做
>
> - 业务方每天手工导出、肉眼筛选，对账耗时且容易出错。
> - 本期目标是把这段人工去掉，不改现有业务流程。
> - 已定：不新增页面，在现有列表上扩展。
>
> ## 02 边界｜哪些能改，哪些绝对不能碰
>
> - 可改：融资申请列表的查询、筛选与导出。
> - 不可改：申请创建、审批流转、状态机逻辑。
> - 模块隔离：不修改公共查询组件的默认行为。
>
> ## 03 约束｜有哪些必须遵守的既有规则
>
> - 客户名称使用模糊筛选，融资状态使用精确筛选。
> - 覆盖单条件、多条件、空结果，并保留既有数据权限。
> - 导出走已有的异步任务通道，不新增同步大查询。
> - 导出的是当前筛选结果；导出任务必须保留 `customer_name`、`status` 和当前用户的数据权限范围。
> - 导出字段严格为 `id`、`customer_name`、`status`、`amount`。
> - 前端必须具备客户名称筛选、融资状态筛选和导出操作；只验收功能和行为，不约束 HTML `id`、`class` 或变量名。
> - 不引入新的第三方依赖。
>
> ## 04 交付物｜最终交什么
>
> - 后端查询接口 + 前端筛选组件 + 导出任务。
> - 接口文档同步更新。
> - 一次结构清晰、可回滚的 PR。
>
> ## 05 验收标准｜怎样证明对
>
> - 开发侧只运行 `../../.venv/bin/python -m pytest -q`。
> - 独立验收由讲师在 workspace 外执行，开发 Agent 不读取独立验收脚本实现。
> - 筛选组合覆盖单条件、多条件、空结果，且不绕过现有数据权限。
> - 导出是当前筛选结果，并保留筛选条件和当前用户权限范围。
> - 导出字段严格等于 `id`、`customer_name`、`status`、`amount`。
> - 前端具备客户名称筛选、融资状态筛选和导出操作，不绑定具体 HTML 命名。

允许 Codex 修改。开发侧完成后只运行：

```bash
../../.venv/bin/python -m pytest -q
```

退出 workspace 后，由讲师运行同一套独立验收，并保存 Demo 2 差异：

```bash
cd ../..
.venv/bin/python instructor/checks/task_a_acceptance.py
./scripts/capture_diff.sh demo2
```

独立验收脚本只在 `instructor/`，不会出现在 `demo12-financing`。落点：五要素的价值不是让 Prompt 更长，而是让“完成”第一次有了共同定义。

## Demo 3｜两个独立上下文｜45 min

Demo 3 的固定顺序是：`reset wrong → developer 输入与测试 → 启动 HTTP 黑盒 → validator 先算期望 → HTTP 取 actual → 报告 BLOCKER → 停旧服务 → developer 修复 → 重启 HTTP 黑盒 → validator 复验`。

### 3A. developer｜先得到“测试全绿，但业务仍错”

讲师先在仓库根目录执行：

```bash
./scripts/restore_demo3_wrong.sh
cd workspaces/demo3-developer
../../.venv/bin/python -m pytest -q tests/test_settlement_developer.py
```

正常结果是 `3 passed`。这里必须保持“汇损 + 退税双候选”的历史错误状态；实现和开发测试同源，全绿不是业务正确性的证明。

从 `workspaces/demo3-developer/` 新开 developer Codex 会话，粘贴下面这段输入：

> 你现在处于 Demo 3 developer 上下文。请读取 `tasks/task-b-development.md`，检查当前 `app/settlement/` 实现，并运行开发侧测试 `../../.venv/bin/python -m pytest -q tests/test_settlement_developer.py`。本阶段只报告当前实现、测试结果和仍需独立验收确认的业务前提，不要读取 validator workspace，不要修改代码，也不要宣布业务验收 PASS。

开发会话展示完成后，在 developer workspace 的另一个终端启动黑盒服务，并保持该终端运行：

```bash
./bin/start-blackbox
# 服务保持在 http://127.0.0.1:8765
```

### 3B. validator｜先形成独立期望，再取得实际输出

暂停 developer Codex 会话，但不要停止黑盒服务。切换到 validator workspace，并从这里新开独立验收 Codex 会话：

```bash
cd ../demo3-validator
```

先粘贴下面的验收输入；在形成 Independent Expectation 之前，validator 只能读取本 workspace 的 Source of Truth 和 Golden Case 输入：

> 你是独立验收角色。先读取 `rules/settlement_source_of_truth.md` 和 `validation/cases.json`，不要读取 developer workspace 的实现、开发测试、解释、计划或聊天记录。请先逐个 case 独立计算 expected mode 与 amount，并把 Independent Expectation 写入 `validation/report.md`；完成期望计算前不要调用实际输出。

“正确答案 6200”来自 Source of Truth 的组合规则和 GC-01 输入，不来自 developer 代码或隐藏验收脚本：

| Case | 独立计算 | Expected |
| --- | --- | --- |
| GC-01 | 汇损 1,200 + 退税 5,000，组合未排除 | `6200 / FX_LOSS_PLUS_TAX_REFUND` |
| GC-02 | 组合被排除，回退退税 | `5000 / TAX_REFUND_ONLY` |
| GC-03 | 只有退税具备资格 | `5000 / TAX_REFUND_ONLY` |
| GC-04 | 退税不具备资格，汇损不能单独申报 | `0 / NO_CANDIDATE` |

确认 Independent Expectation 已写入报告后，在 validator workspace 执行唯一的实际结果入口：

```bash
../../.venv/bin/python bin/actual-output validation/cases.json
```

再粘贴下面这段输入，要求 validator 将 HTTP 返回与独立期望逐项比较：

> 现在读取刚才的 HTTP actual output，与 `validation/report.md` 中的 Independent Expectation 比较，补充 Actual output、Mismatches 和 Overall。不要读取 developer workspace。错误态预期：GC-01 actual 为 `5000 / TAX_REFUND_ONLY`，因此必须报告 `Overall = BLOCKER`。

错误态必须稳定得到：

```text
GC-01 expected = 6200 / FX_LOSS_PLUS_TAX_REFUND
GC-01 actual = 5000 / TAX_REFUND_ONLY
Overall = BLOCKER
```

### 3C. 修复与复验｜必须停止旧服务并重启

出现 BLOCKER 后，先在黑盒服务终端按 `Ctrl-C` 停止旧进程。再切回 developer workspace，恢复或继续 developer Codex 会话，粘贴：

> 根据独立验收报告中的 BLOCKER 修复 `app/settlement/` 候选判定逻辑，使组合候选优先、只有组合被排除时才回退到退税单候选。不要修改 Source of Truth 或 validator workspace。完成后运行 `../../.venv/bin/python -m pytest -q tests/test_settlement_developer.py`，报告修改文件和测试结果，不自行宣布独立验收 PASS。

```bash
cd ../demo3-developer
../../.venv/bin/python -m pytest -q tests/test_settlement_developer.py
```

测试全绿后，必须重新启动黑盒服务；旧进程不会自动加载刚刚修改的代码：

```bash
./bin/start-blackbox
# 保持 http://127.0.0.1:8765 运行
```

回到 validator workspace，在原独立验收会话中重新取得实际输出：

```bash
cd ../demo3-validator
../../.venv/bin/python bin/actual-output validation/cases.json
```

修复后应为 `Overall = PASS`，GC-01 应为 `6200 / FX_LOSS_PLUS_TAX_REFUND`。如果仍看到 `5000 / TAX_REFUND_ONLY`，先检查是否真的停止并重启了 `127.0.0.1:8765` 的旧服务，再重复 actual-output；不要复制 developer 源码到 validator。

确定性兜底仅供彩排恢复使用：先停止黑盒服务，再从仓库根目录执行 `./scripts/restore_demo3_fixed.sh`；恢复后仍要重新启动黑盒服务，并通过 validator 的 HTTP 入口复验。

## Demo 4｜demo4-sedimentation｜同 workspace，新会话｜15 min

从 Demo 3 正确修复状态开始，使用独立的 Demo 4 workspace：

```bash
./scripts/reset_demo4.sh
cd workspaces/demo4-sedimentation
```

在这里新开第一个 Codex 会话，粘贴 `instructor/prompts/demo4/04-retro.md`。让复盘角色读取 `reports/demo3-validation.md`，把可复用规则写入：

- `AGENTS.md`
- `validation/checklist.md`

初始 `AGENTS.md` 不含“双候选优先”规则；复盘后必须出现“组合候选先评估，只有被明确排除才回退到退税单候选”的规则。展示 diff 后，关闭旧 Codex 会话。

重点：仍在同一个 `demo4-sedimentation` workspace，但必须新开一个全新 Codex 会话：

```bash
# 仍在 workspaces/demo4-sedimentation，不要 cd 到别处
```

新会话只粘贴 `tasks/task-b-variant.md` 并让它依赖会话启动时加载的项目级规则，不读取 `rules/`、`validation/`、`app/`、`tests/`，也不依赖历史聊天。预期：`FX_LOSS_PLUS_TAX_REFUND`，金额 `11,000`。

如果复盘现场需要确定性兜底：

```bash
cd ../..
./scripts/restore_demo4_learned.sh
```

## Reset / restore 对照

| 场景 | 起始状态 | 命令 |
| --- | --- | --- |
| Demo 1 | `demo12-financing` 融资申请 baseline | `./scripts/reset_demo1.sh` |
| Demo 2 | 同一个 `demo12-financing` baseline | `./scripts/reset_demo2.sh` |
| Demo 2 兜底 | `demo12-financing` 参考实现 | `./scripts/restore_demo2_reference.sh` |
| Demo 3 developer + validator | 错误实现、开发测试全绿 | `./scripts/restore_demo3_wrong.sh` |
| Demo 3 developer | 正确修复态 | `./scripts/restore_demo3_fixed.sh` |
| Demo 4 | 正确修复项目、未沉淀规则 | `./scripts/reset_demo4.sh` |
| Demo 4 兜底 | 已沉淀规则 | `./scripts/restore_demo4_learned.sh` |

本轮结构验收：

```bash
.venv/bin/python scripts/acceptance_check.py
```

该命令只做自动检查，不启动真实课堂流程，也不让 Codex 执行任务 A/B。
