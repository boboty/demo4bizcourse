# 全 Demo 最终 QC 报告

日期：2026-09-14
范围：D0 / D1 / D3 / D4 全链路课堂友好化验收（不重新设计 Demo，不改变已锁定的核心行为）。
Canonical classroom entry：`instructor/DEMO-RUNBOOK.html`

## 1. 本轮改了哪些课堂可见文本

### 1.1 融资状态中文映射（第一优先级）

统一映射（页面显示层，`value` 与 API 参数保持英文不变）：

| 内部枚举 | 页面显示 |
| --- | --- |
| `SUBMITTED` | 待审核 |
| `APPROVED` | 已通过 |
| `REJECTED` | 未通过 |
| `FUNDED` | 已放款 |

导出任务自身的排队状态：`QUEUED` → 已提交。

应用方式：在每个页面的 `<script>` 里新增 `STATUS_LABELS` / `JOB_STATUS_LABELS` 常量和
`statusLabel()` / `jobStatusLabel()` 两个纯显示函数；下拉框选项改为
`<option value="SUBMITTED">待审核</option>` 这种"value 英文、文本中文"的写法；表格状态列、
导出反馈里的 `job id` → "任务编号"、`status` → "任务状态"、筛选条件回显里的 `status=` 值，全部
经过 `statusLabel()`/`jobStatusLabel()`。已确认页面内没有对 `<option>` 文本或 `.pill` 文本做
字符串匹配的测试或脚本依赖（现有测试/脚本都走真实 HTTP API，用的是英文枚举）。

覆盖的页面（按用户点名的检查范围逐一核对，无遗漏）：

- D1：`instructor/reference/d1-handoff-completed/static/index.html`（reference/completed）、
  `instructor/baselines/d1-handoff/stage-0/static/index.html`、
  `instructor/baselines/d1-handoff/stage-1/static/index.html`（课堂接手起点，
  `workspaces/d1-handoff` 由 `reset_d1_handoff.sh` 从这两份重放生成，已改源头）
- D1 / Demo1 / Demo2 共用资产：`instructor/baselines/demo12-financing/static/index.html`
  （Demo1/Demo2 起点 baseline）、`instructor/baselines/demo12-reference/static/index.html`
  （Demo2 fallback 参考实现，`restore_demo2_reference.sh` 会把它同步进
  `workspaces/demo12-financing`）
- D3：`instructor/baselines/demo3-developer/static/index.html`（wrong 状态起点）、
  `instructor/baselines/demo3-fixed/static/index.html`（fixed 状态）
- D4：`instructor/baselines/demo4-sedimentation/static/index.html`（pre-sedimentation）、
  `instructor/baselines/demo4-sedimented/static/index.html`（sedimented）
- 对应的 `workspaces/` 实时副本（`demo3-developer`、`demo4-sedimentation`、
  `demo12-financing`）已同步为相同内容，并用 `reset_demo1.sh` / `reset_demo3_developer.sh` /
  `reset_demo4.sh` 重新生成校验，digest 与 baseline 一致。

另外为一致性也顺带处理了 `instructor/baselines/d1-financing-minimal/static/index.html`
（D1-RUNBOOK.md 末尾保留的 Level 1/2/3 对比实验用的共享 baseline，表格状态列同样加了
`statusLabel()`），并用 `scripts/reset_d1.sh all` 重新生成了 `workspaces/d1-level1/2/3`
三个工作目录，`scripts/d1_verify_setup.py` 复跑仍为 `OVERALL: PASS`。

**唯一未改动**：`instructor/baselines/d0-first-loop/static/index.html`（含
`workspaces/d0-first-loop` 副本）。原因见第 2 节——曾经尝试过同样的改动，但会作废一份真实
live-agent fallback 预跑证据的 digest，已撤销。

### 1.2 Golden Case 展示 label 中文化（D3/D4 关键验收输出）

`validation/cases.json`（`instructor/baselines/demo3-validator/`、
`workspaces/demo3-validator/`）与 `golden/cases.json`
（`instructor/baselines/demo4-sedimented/`）里的展示用 `label` 字段：

- GC-01 `APPROVED` → `已通过`
- GC-02 `REJECTED` → `未通过`
- GC-03 `MIXED` → `混合状态`
- GC-04 `TENANT_SCOPE` → `租户权限`

`query.status` 等真正参与验证的技术值（`APPROVED`/`REJECTED`/...）未改动。demo3_validator.py
和 golden/check_export_eligibility.py 的打印格式不变（`{id} {label} {PASS/FAIL}`），实测输出
变为 `GC-02 未通过 FAIL`（详见第 3 节验证结果）。

同步更新了依赖旧字符串的验收/文档：

- `scripts/acceptance_check.py`：D4 注入回归检查从断言 `"REJECTED" in blocked_result.stdout`
  改为断言 `"未通过" in blocked_result.stdout`（连同 `GC-02` 一起判定，验收强度不变——
  GC-02 与 REJECTED 状态的映射关系由 `cases.json` 固定，且未改动）。
- `instructor/ACCEPTANCE-CHECKLIST.md`：两处 `GC-02 REJECTED` 引用更新为
  `GC-02（未通过 / REJECTED）` / `GC-02 未通过`。
- `instructor/DEMO-RUNBOOK.html`：3B/3G 的"讲师预跑实测"引用块、4E 的确定性 BLOCK 输出块，
  同步改成新的中文 label，避免 Runbook 里的"预期输出"和真实终端输出不一致。
- `instructor/baselines/demo4-sedimented/reports/demo3-validation.md`、
  `instructor/baselines/demo4-sedimentation/reports/demo3-validation.md`、
  `workspaces/demo4-sedimentation/reports/demo3-validation.md`、
  `instructor/d3/defect-report.md`：报告里的 Golden Case 表格同步改为中文 label（数字结果、
  根因描述未改动）。

**未改动**：Runbook 里 `<div class="prompt">` 内、真实发给 Agent 的缺陷单文本（3E 的
`d3-defect` prompt）——里面提到 `GC-02 REJECTED`、`GC-03 MIXED（不筛状态）` 是在陈述业务事实
（这条 Golden Case 对应哪个查询条件），不是在复现脚本打印格式，且这段文本是课堂里逐字发给
开发 Agent 的固定任务，按约束不做核心行为改动。

### 1.3 Runbook 非必要英文清理（`instructor/DEMO-RUNBOOK.html`）

只处理正文、课堂提示、按钮文案、讲师旁白（`<div class="callout/warn/blocker/evidence">`、
`<h3>`、`<p>`），**没有**改动：
- 发给 Agent 的 `<div class="prompt">` 任务文本（D0/D1/D3/D4 的每一句指令，含 4B 的
  `d4-retro` 事故复盘任务、4C 的 `d4-fresh-task` 维护任务）——这些是已经验证过的课堂核心脚本；
- `<div class="code">` 里的真实命令和真实终端输出（`pytest -q` 的 `passed/failed`、
  `Export eligibility Golden Case: FAIL`、`OVERALL: BLOCKED/PASS` 等工具原样输出）；
- 所有 `workspaces/...`、`instructor/...` 路径和脚本文件名。

具体替换：`D1 Fresh Session`→`D1 全新会话`；D0 观察链
`Run → FAIL → Read/Search → Observe → Edit → Run → PASS` → `运行 → 失败 → 读取/搜索 →
判断 → 修改 → 再运行 → 通过`（两处：hero 摘要列表 + D0 callout）；`baseline`（叙述性用法，
非路径）→ `基线`；`developer`/`Developer`（角色词，非 `workspaces/demo3-developer` 路径）→
`开发侧`；`Validator`→`独立验收侧`；`fallback`（叙述性用法，非 `instructor/d?/fallback/` 路径
和脚本名）→`兜底`/`兜底方案`；`workspace`（叙述性用法，非 `workspaces/...` 路径）→`工作目录`；
`policy gate`（讲师旁白里的用法）→`规则门禁`；`Golden Case` 首次出现处写成
`黄金样例（Golden Case）`，此后正文统一用`黄金样例`（脚本真实打印的
`Export eligibility Golden Case: FAIL` 等英文标题保留不译）；`Agent` 保留原词，在第一句自然
出现处补充一次`Agent（智能体）`。

**范围说明**：`instructor/DEMO-RUNBOOK.md`（694 行的详细版）中约有一半篇幅是明确标注为历史
材料的旧"汇损 + 退税候选"结算版 Demo 3（第 226 行起，文中已自带说明："本节沿用的'汇损 +
退税候选'是更早期的材料，只作历史参考，不再是课堂主线"，且 canonical HTML 完全不引用这部分）。
本轮没有对这段历史材料做术语替换——它已经是明确标注的历史存档，替换价值低、且风险是
误伤历史证据的可读性。`.md` 中与 `.html` 内容重叠的当前主线部分（prep/D0/D1）本轮未额外
复刻同一批替换，因为 `scripts/acceptance_check.py` 对两个文件有若干"必须逐字相同"的
标记字符串校验（如 Demo2 完整 Spec 文本），逐一在 `.md` 里手动同步风险较高、收益有限
（`.html` 才是 canonical classroom entry）。这是一个有意的范围取舍，供后续单独排期。

## 2. 哪些技术英文刻意保留以及原因

| 保留内容 | 原因 |
| --- | --- |
| API 查询参数 `status=APPROVED/REJECTED/...`、下拉框 `value` 属性 | 接口契约不变，`task_a_acceptance.py`、`d1_handoff_verify_setup.py` 等脚本按字面值断言这些字符串存在 |
| Python 常量、JSON 数据（`cases.json` 的 `query.status`、`known_applications.json` 的 `status`/`tenant`） | 内部枚举值，测试和独立验收依赖精确匹配 |
| `pytest`/终端真实输出（`passed`/`failed`/`PASS`/`FAIL`/`OVERALL: BLOCKED`） | 工具真实输出，按约束不强行翻译 |
| Runbook 里发给 Agent 的 `<div class="prompt">` 任务文本 | 已验证过的课堂核心脚本，翻译措辞可能改变 Agent 的理解方式，超出"文本清理"范围 |
| `instructor/baselines/d0-first-loop/static/index.html`（及 `workspaces/d0-first-loop` 副本）里的融资状态英文 | 见下方"已知风险"说明：这份 baseline 的 tree digest 被 `instructor/d0/fallback/snapshot.json` 记录的一次真实 live-agent 预跑固定引用；本轮曾尝试同步中文映射，但会让 `python scripts/d0_verify.py` 的"D0 fallback 与课堂使用同一个 baseline"检查失败（因为 fallback 快照的 digest 对应的是旧内容）。D0 的课堂链路本身不浏览这个页面（D0 全程是 pytest 驱动），中文化这里没有课堂收益，却会作废一次真实 Agent 预跑证据，因此撤销了这处改动，保持原样 |
| `Agent`、`Session`、`Golden Case`（脚本原样输出部分）、`Source of Truth` | 属于课程既定技术词汇或工具原样输出，不属于"非必要英文" |
| `instructor/DEMO-RUNBOOK.md` 中明确标注历史的旧结算版 Demo 3（第 226 行起，含"汇损"、"退税候选"、"FX_LOSS_PLUS_TAX_REFUND"、端口 `8765` 等） | 文档内已自我声明"只作历史参考，不再是课堂主线"，canonical `.html` 不引用，符合"明确标记为历史、且不再被引用可以保留"的删除/保留判断标准 |

## 3. D0/D1/D3/D4 各自最终验证结果

全部在改动完成后于仓库根目录用根 venv 重新跑通：

```
.venv/bin/python scripts/acceptance_check.py   → OVERALL: PASS
.venv/bin/python scripts/d0_verify.py          → OVERALL: PASS
./scripts/d1_handoff_verify_setup.py           → OVERALL: PASS
.venv/bin/python scripts/d1_verify_setup.py    → OVERALL: PASS（Level 1/2/3 对比实验，附带检查）
```

分项手动核对（均为真实命令，非脚本代跑）：

- **D0**：`reset_d0.sh` → 红灯 `4 failed, 4 passed`（可重复）；目标态 `8 passed`；fallback 与
  `instructor/d0/fallback/` 的一次真实 live-agent 预跑证据（digest 一致）保持有效。
- **D1**：`reset_d1_handoff.sh` 后浏览器起点只有客户名称筛选，状态筛选/导出控件均未出现
  （中文进度提示 `客户名称筛选 ✓ / 融资状态筛选 ×（下一步）/ 导出 ×（下一步）`）；
  `restore_fixed` 后三项功能齐全，状态下拉框显示"待审核/已通过/已放款/未通过"，导出反馈显示
  "任务编号 ... · 任务状态 已提交 · 筛选条件 ... status=未通过 · 共 1 条记录"。
- **D3**：wrong 状态下未通过（REJECTED）记录仍可查询，"放款处理导出"错误导出 1 条
  （中文页面确认，见第 4 节）；`demo3_validator.sh` 独立验收在 wrong 状态下
  `GC-02 未通过 FAIL`、`Overall: BLOCKER`；fixed 状态下 `Overall: PASS`。
- **D4**：fixed（沉淀）状态下未通过记录查询 1 条、导出 0 条（"当前筛选状态不满足放款导出条件，
  无可导出记录"）；`inject_demo4_regression.sh` 注入回归后查询 1、导出 1，
  `verify.sh` 同时跑完开发测试（`pytest` 4 failed）与黄金样例（`GC-02 未通过 FAIL`），
  最终 `OVERALL: BLOCKED`；`restore_demo4_fixed.sh` 恢复后查询 1、导出 0，
  `verify.sh` 回到 `OVERALL: PASS`，且未触碰已沉淀的规则文档/Golden Case/verify.sh
  （`tree_digest` 校验通过）。

## 4. 浏览器页面检查结果

用内置 Browser 面板对 D1（`8010`）、D3（`8030`）、D4（`8050`）三个真实服务逐一操作
（不只 curl/API），重点看中文状态显示和导出反馈：

- **D1**（`workspaces/d1-handoff`，先看接手前状态、再 `restore_fixed` 看完整态）：
  接手前列表状态列显示"待审核/已通过/已放款/未通过"；完整态下拉框选中"未通过"→筛选→
  "导出当前筛选结果"，反馈条显示
  `导出任务已创建：任务编号 xxx · 任务状态 已提交 · 筛选条件 customer_name=(空)，
  status=未通过 · 共 1 条记录`。
- **D3**（`workspaces/demo3-developer`，wrong 状态）：状态选"未通过"→筛选→
  "放款处理导出"，反馈显示"共 1 条记录"（即 REJECTED 记录被错误导出，符合 D3 教学预期的
  "看起来正常、实际违规"状态）。
- **D4**（`workspaces/demo4-sedimentation`，fixed/沉淀状态）：同样操作，反馈显示
  "共 0 条记录（当前筛选状态不满足放款导出条件，无可导出记录）"，列表仍能查到该条未通过记录 —
  与 D3 收口时的正确行为一致。

三个页面下拉框选项、表格状态列、导出反馈文案完全统一（"待审核/已通过/未通过/已放款"、
"任务编号/任务状态"），未出现"是不是换了一个功能"的用词不一致。

## 5. D1→D3→D4 产品连续性核对

页面标题（"融资申请"）、筛选区域布局、状态名称映射、表格列（申请编号/客户/状态/金额）、
空结果表达、金额格式（`toLocaleString()` 千分位）、分页表达（"第 N 页 / 共 M 条"）三个 Demo
完全一致。

发现的唯一差异：D1 的导出按钮文案是"导出当前筛选结果"，D3/D4 是"放款处理导出"。**判断为
有意保留、不强行统一**：D1 的任务边界是开放式的（"导出走已有异步任务通道，导出当前筛选结果"，
学员/Agent 自己决定怎么实现和命名），D3/D4 在剧情上已经进入"这是一个具体业务动作（放款
处理）"的阶段，用更具体的业务语言是合理的教学递进，而不是随意的用词漂移。Runbook 里 D1 收口
到 D3 之间已经有明确的过渡句（"接第三讲的问题：它把页面做完了...但这是不是就等于它做对了？"），
不会让课堂产生"换了功能"的困惑，因此未强行统一（统一会绑死 D1 开放任务的实现自由度）。

## 6. 课堂命令/目录/端口检查

- `../../.venv/bin/python` 从 `workspaces/<name>/` 内执行时，两级 `..` 正确回到仓库根目录
  （`workspaces/` 与其子目录各一级），与 `scripts/acceptance_check.py` 中启动开发服务器的
  真实调用方式一致，已通过全部三个验收脚本的真实执行验证。
- 端口核对：D1 `8010`、D3 `8030`、D4 `8050`，Runbook 文案与 `d1_handoff_serve.sh` /
  `demo3_serve.sh` / `demo4_serve.sh` 的固定端口一致；本轮浏览器检查逐一实际连接确认。
- `stop`/`serve`/`reset`/`restore` 脚本成对存在：`d1_handoff_serve.sh` ↔
  `d1_handoff_stop.sh`；`demo3_serve.sh` ↔ `demo3_stop.sh`；`demo4_serve.sh` ↔
  `demo4_stop.sh`；均已在本轮验证中实际调用过。
- 根目录未见裸 `pytest` 被重新引入为"全课程验收命令"——canonical 验收入口仍是
  `scripts/acceptance_check.py` + `scripts/d0_verify.py` + `scripts/d1_handoff_verify_setup.py`。

## 7. Stale reference / 退休故事残留扫描

- 确认删除（明确退休、无任何引用、且不影响历史证据）：
  `instructor/reference/settlement_source_of_truth.md`、
  `instructor/reference/validation/`（`cases.json`、`checklist.md`、
  `independent-validation.md`）——这是比 `DEMO-RUNBOOK.md` 里保留的历史"汇损+退税候选"章节
  更早、完全孤立的旧结算 Demo 验收资产，仓库内没有任何脚本、文档或 HTML 引用它们
  （删除前后 `scripts/acceptance_check.py` 均为 `OVERALL: PASS`）。
- `settlement`/`FX_LOSS`/`8765`/`汇损`/`退税候选` 等字样在 canonical Runbook（`.html`）、
  `README.md`、`ACCEPTANCE-CHECKLIST.md`、当前脚本、当前 baseline 中未发现（除
  `ACCEPTANCE-CHECKLIST.md` 里"已删除"的否定性确认，以及 `DEMO-RUNBOOK.md` 中已标注历史的
  章节，两者都是预期状态，不算残留）。
- `restore_demo4_before.sh`、`restore_demo4_learned.sh`、`instructor/golden/`、
  `instructor/baselines/demo4-learned/` 均已确认不存在；仅在验收脚本和 checklist 里以
  "已删除"的否定断言形式出现，符合预期。
- 未发现指向不存在文档路径的死链接。

## 8. Runbook 可操作性检查

程序化核对（`instructor/DEMO-RUNBOOK.html`）：
- 所有 `id` 唯一，无重复；
- 所有 `data-copy` 按钮都能找到对应的 `id`（复制按钮内容与目标一致）；
- 所有导航 `data-go` 都能定位到对应 section 的 `id`（锚点导航正常）；
- 每个关键动作块的命令都是自包含的 `cd` + 命令，未见"沿用上一段隐含 cwd"的写法；
- 成功态（`callout`）、异常态（`warn`）、阻断态（`blocker`）在每个关键节点都有，且紧跟明确的
  下一步指引或 fallback 脚本。

## 9. Acceptance 总结果

```
OVERALL: PASS   （scripts/acceptance_check.py，改动前后各跑一次，全绿）
OVERALL: PASS   （scripts/d0_verify.py）
OVERALL: PASS   （scripts/d1_handoff_verify_setup.py）
OVERALL: PASS   （scripts/d1_verify_setup.py，Level 1/2/3 附带检查）
```

## 10. 已知风险

无课堂阻断项。

需要留意但不阻断上课的两点：
1. `instructor/DEMO-RUNBOOK.md`（694 行详细版）的当前主线部分（prep/D0/D1）未与
   `.html` 做逐字同步的术语清理，两份文件在"非必要英文"用词上可能存在少量不一致（不影响
   canonical `.html` 的课堂使用，`.md` 目前更多是背景参考）。
2. `instructor/baselines/d0-first-loop`（含 `workspaces/d0-first-loop`）的融资状态列仍是英文
   原文（详见第 2 节），因为它绑定着一次真实 live-agent fallback 预跑证据的 tree digest，
   本轮判断"D0 课堂全程不浏览这个页面、中文化零收益，却有证据失效风险"，故意不改。如果后续
   需要覆盖，需要先确认能否重新预跑生成 D0 fallback snapshot，而不是直接改文件。
