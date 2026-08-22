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

### 固定顺序

`restore wrong → 开发测试 3 passed → 启动 HTTP 黑盒 → 展示 Source of Truth → 学员算出 6200 → 新开 validator → BLOCKER → 揭示实现与测试同源同错 → 第一次新开 developer 修复 → 4 passed → 重启 HTTP 黑盒 → 回原 validator 复验 PASS`

### 3A. 历史开发状态｜先看到 3 passed

讲师从仓库根目录执行：

```bash
./scripts/restore_demo3_wrong.sh
cd workspaces/demo3-developer
../../.venv/bin/python -m pytest -q tests/test_settlement_developer.py
```

预期：

```text
3 passed
```

此时**不要开 Developer Codex**。这只是一个已经“开发完成”的历史状态：实现存在、开发测试全绿，但我们还没有证明业务正确。

讲师口播：

> 这是一个已经开发完成的历史任务。实现有了，开发测试也是全绿的。先别急着说它对。

然后在另一个终端启动黑盒服务，并保持运行：

```bash
cd workspaces/demo3-developer
./bin/start-blackbox
```

预期：

```text
blackbox listening on http://127.0.0.1:8765
```

### 3B. 先把业务尺子摆出来｜6200 必须有客观来源

仍在 `workspaces/demo3-developer/`，向学员展示独立验收方使用的业务事实源和 Golden Case 输入：

```bash
cat ../demo3-validator/rules/settlement_source_of_truth.md
cat ../demo3-validator/validation/cases.json
```

只抓 GC-01：

- `fx_loss_eligible = true`，金额 `1200`
- `tax_refund_eligible = true`，金额 `5000`
- `combined_excluded = false`

Source of Truth 明确规定：

1. 汇损和退税同时满足时，先评估“汇损 + 退税”组合候选。
2. 组合候选未被排除时，返回 `FX_LOSS_PLUS_TAX_REFUND`。
3. 金额 = 汇损金额 + 退税金额。
4. 只有组合候选被排除后，才允许回退 `TAX_REFUND_ONLY`。

**课堂暂停：**

> 按照这份业务规则，GC-01 应该是多少？

预期学员得到：

```text
1200 + 5000 = 6200
FX_LOSS_PLUS_TAX_REFUND
```

这里要明确：**6200 不是讲师临时宣布的答案，也不是 Validator 自己猜的答案，而是由 Source of Truth + Golden Case 输入推导出来的。**

### 3C. 独立 Validator｜一句话执行既有验收规则

切换到 validator workspace：

```bash
cd ../demo3-validator
# 从这里新开 Luna + High
```

只发送一句：

> 执行 `validation/independent-validation.md`。

不要在 Runbook 里重新展开一套 Validator Prompt。`validation/independent-validation.md` 已经定义了角色、隔离规则、步骤和报告格式；它会先根据 Source of Truth + cases 形成 Independent Expectation，再通过 HTTP 黑盒取得 Actual Output。

预期：

```text
Overall: BLOCKER

GC-01
Expected: FX_LOSS_PLUS_TAX_REFUND / 6200
Actual:   TAX_REFUND_ONLY / 5000

GC-02 ~ GC-04: PASS
```

报告写入：

```text
validation/report.md
```

课堂提醒：仍然是 Luna + High，没有偷偷换更强模型。变化的是**理解来源独立了**。

### 3D. 揭开为什么“测试全绿还是错”

Validator 报告 BLOCKER 后，回 developer workspace：

```bash
cd ../demo3-developer
sed -n '1,220p' app/settlement/service.py
sed -n '1,240p' tests/test_settlement_developer.py
```

只抓 GC-01，不讲完整代码。

开发实现里的关键错误：

```python
if refund_ok:
    return {"mode": "TAX_REFUND_ONLY", "amount": refund}
```

开发测试里的关键错误：

```python
assert evaluate_candidate(case) == {
    "mode": "TAX_REFUND_ONLY",
    "amount": 5000.0,
}
```

屏幕上形成三层证据：

```text
Source of Truth：两者都成立 + 组合未排除 → 6200
开发实现：                                  → 5000
开发测试：                                  → 也把 5000 当正确答案
```

讲师口播：

> 为什么代码错了，测试还能全绿？因为这个历史开发状态里，开发实现和开发测试来自同一个需求理解源。需求一开始被理解成了“两个候选都存在时选退税”，于是代码按这个理解写，测试也按这个理解验证。代码给 5000，测试也认为 5000 正确，所以当然全部通过。

继续强调：

> 这不是测试没覆盖。第一条测试已经覆盖了两个候选同时存在的场景。问题是测试自己也把错误答案当成了正确答案。

落点：

> **测试全绿，只能证明实现符合这套测试；如果测试和实现来自同一个错误理解，它证明不了业务理解本身是对的。**

最后再给这个现象命名：

> **同源验证抓不到共同理解偏差。**

### 3E. 第一次新开 Developer Agent｜把缺陷交回开发责任

**到这里才第一次在 `workspaces/demo3-developer/` 新开 Luna + High Developer Codex。**

给 Developer 完整缺陷单：

> 独立验收发现一个 BLOCKER，请修复当前实现和开发侧测试。
>
> 业务规则：
> - 当汇损候选和退税候选同时具备资格时，必须先评估“汇损 + 退税”组合候选。
> - 如果组合候选未被排除，应返回 FX_LOSS_PLUS_TAX_REFUND。
> - 金额 = 汇损金额 + 退税金额。
> - 只有组合候选被明确排除后，才允许回退到 TAX_REFUND_ONLY。
> - 如果只有退税候选具备资格，则返回 TAX_REFUND_ONLY。
> - 如果退税候选不具备资格，本演示返回 NO_CANDIDATE。
>
> 独立验收发现：
> GC-01：
> fx_loss_eligible = true
> fx_loss_amount = 1200
> tax_refund_eligible = true
> tax_refund_amount = 5000
> combined_excluded = false
>
> 当前系统实际：
> TAX_REFUND_ONLY / 5000
>
> 正确结果：
> FX_LOSS_PLUS_TAX_REFUND / 6200
>
> 请：
> 1. 检查当前实现和开发测试为什么会得到错误结果。
> 2. 修正实现。
> 3. 修正开发侧测试。
> 4. 运行：`../../.venv/bin/python -m pytest -q tests/test_settlement_developer.py`
> 5. 汇报修改和测试结果。

真实彩排预期：

```text
4 passed
```

讲师点一句：

> 修复共同理解偏差，不只是改代码，还要把同源的错误测试一起纠正。

### 3F. 修复后必须重启黑盒

**不要漏。旧黑盒进程是在修复前启动的。**

回到运行黑盒的终端：

```bash
Ctrl+C
./bin/start-blackbox
```

预期：

```text
blackbox listening on http://127.0.0.1:8765
```

如果修复后 Validator 仍看到 5000，第一件事就是检查旧服务是否真的停止并重启。

### 3G. 回到原来的 Validator 会话复验

不要新开 Validator，不告诉它 Developer 具体改了哪行代码。

回到刚才那个 validator Codex 会话，只发送：

> 开发方已提交修复，请按 `validation/independent-validation.md` 重新执行独立验收。

预期：

```text
GC-01 PASS  FX_LOSS_PLUS_TAX_REFUND / 6200
GC-02 PASS
GC-03 PASS
GC-04 PASS

Overall: PASS
```

报告继续更新 `validation/report.md`。

### Demo 3 收口

按这个顺序说：

1. **救回这一次的，不是更多测试，而是第二个独立理解源。**
2. **写代码的 AI，不适合完全自己验自己。**
3. **关键不是换一个更强的模型，而是验证要有独立的理解来源。**

模型控制说明：Developer 和 Validator 都使用 Luna + High。课堂可补一句：

> 你们注意，我这里没有偷偷换一个更强的模型。还是同一档模型，只是不给它看开发者的答案，让它重新从业务事实算一遍。

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