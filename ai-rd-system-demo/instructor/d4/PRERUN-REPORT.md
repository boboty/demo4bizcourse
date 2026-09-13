# D4 预跑报告

## 本轮：3 次真实 D4 live Agent 彩排

不同于此前只跑 `scripts/acceptance_check.py` 的自动化链路，这三次是三个完全独立、彼此
没有历史聊天记录的真实 Agent 会话（每次 D4-2、D4-3 各另开一个全新 Agent），在真实
`workspaces/demo4-sedimentation` 上执行，覆盖：

```
reset → D4-2 Agent 真实沉淀（新会话）→ 关闭会话
      → D4-3 全新 Session 完成 exported_by 维护任务，且必须自己发现规则/verify（新会话）
      → inject_demo4_regression.sh → verify.sh 确定性 BLOCK
      → restore_demo4_fixed.sh → verify.sh 确定性 PASS
```

D4-2、D4-3 收到的任务文本，与 `instructor/prompts/demo4/01-retro-sedimentation.md`、
`02-fresh-session-maintenance-task.md` 里可复制的那一句完全一致，没有额外提示；D4-3 的任务
文本里没有出现"规则""verify""golden"等字眼，规则/验证的发现完全靠它自己读工程现场。
三次都只发了一条任务消息，过程中没有讲师/我追加任何补充提示或纠正。

### Run 1

- D4-2：耗时 3m31s。主动读取 `reports/demo3-validation.md`：**是**（读取顺序中第 3 个文件）。
  产出四类资产：规则文档 `docs/rules/export-eligibility.md`；独立 Golden Case
  `scripts/golden_case_export_eligibility.py`（用 `TestClient` 黑盒调用，不 import
  service 内部，且额外补了两条"仍可查询"的用例）；统一入口 `verify.sh`（先 pytest 再单独跑
  golden 脚本，两段分别打印结果）；工程记忆 `AGENTS.md` 指向前三者。`service.py` 只把重复的
  规则注释收敛成一句指针，`eligible_rows` 等实现结构/命名未变。验证：`./verify.sh` →
  `19 passed` + Golden 6 项全 PASS，`Overall: PASS`。
- D4-3：耗时 1m3s。主动读到 `docs/rules/export-eligibility.md`：**是**。运行 `./verify.sh`
  （而不只是 `pytest`）：**是**。是否碰过 Golden 期望值：**否**（自报未修改
  `scripts/golden_case_export_eligibility.py`，只新增 payload 字段）。
- `inject_demo4_regression.sh`：注入成功（标记行未被改写）。
- `verify.sh`（注入后）：`pytest` 出现 `4 failed, 15 passed`，退出码 1，**确定性 BLOCK**。
  但因为这次 Agent 写的 `verify.sh` 用了 `set -euo pipefail`、pytest 和 golden 脚本按顺序
  直接调用，pytest 失败后脚本提前退出，没有走到 Golden 脚本那一步，所以这次没有看到独立打印的
  `Golden Case: FAIL` / `OVERALL: BLOCKED` 字样——阻断信号本身是确定性的（非零退出码 + 明确指向
  业务断言的失败信息），只是这次没有复现我方参考实现里"两段都跑完再报总状态"的呈现方式。
- `restore_demo4_fixed.sh`：`verify.sh` 恢复到 `19 passed` + Golden 6 项全 PASS。
- 是否需要讲师补提示：**否**。

### Run 2

- D4-2：耗时 3m45s。主动读取 `reports/demo3-validation.md`：**是**（读取顺序中第 3 个文件）。
  产出：规则文档 `docs/rules/export_eligibility.md`；Golden Case 组织成独立 pytest 文件
  `tests/golden/test_export_eligibility_golden_cases.py`（复刻 GC-01~GC-04，文件头注释显式写明
  "不要因为看起来和开发测试重复就删除/合并"）；`verify.sh` 只更新了注释，逻辑仍是单条
  `pytest -q`（因为新用例放在 `tests/` 下会被自动收集，这个变体没有把 Golden Case 做成脚本
  层面独立于 pytest 的第二道调用）；`AGENTS.md` 更新指向前述资产。`service.py` 同样只收敛
  注释，未动逻辑/命名。验证：`./verify.sh` → `23 passed`（19 开发测试 + 4 条 Golden）。
- D4-3：耗时 1m41s。主动读到 `docs/rules/export_eligibility.md` 和
  `tests/golden/test_export_eligibility_golden_cases.py`：**是**。运行 `./verify.sh`：**是**。
  是否碰过 Golden 期望值：**否**。
- `inject_demo4_regression.sh`：注入成功。
- `verify.sh`（注入后）：单条 `pytest -q` 里同时出现 4 条开发测试失败 + 3 条
  `tests/golden/test_export_eligibility_golden_cases.py` 内的 Golden 用例失败（`test_gc02_*`
  `test_gc03_*` `test_gc04_*` 按名字可见），`7 failed, 16 passed`，**确定性 BLOCK**，退出码非零。
  因为 Golden Case 本身就是 pytest 用例、和开发测试同一次 `pytest -q` 一起跑，这个变体没有
  Run 1 那种"提前退出、Golden 步骤没执行"的问题。
- `restore_demo4_fixed.sh`：`verify.sh` 恢复到 `23 passed`。
- 是否需要讲师补提示：**否**。

### Run 3

- D4-2：耗时 4m10s。主动读取 `reports/demo3-validation.md`：**是**（读取顺序中第 3 个文件）。
  产出：规则文档 `docs/rules/export_eligibility.md`；独立脚本
  `scripts/golden_case_check.py`（期望值直接手写在脚本里，不 import
  `EXPORT_ELIGIBLE_STATUSES`）；`verify.sh` 是真正的两步入口（先 pytest 再单独跑 golden 脚本，
  各自失败都会让整体非零退出）；`AGENTS.md` 更新指向前述资产。`service.py` 同样只收敛注释。
  验证：`./verify.sh` → `19 passed` + Golden 5 项全 PASS（含额外的 tenant_scope 字段检查），
  `Overall: PASS`。
- D4-3：耗时 1m25s。主动读到 `docs/rules/export_eligibility.md` 和
  `scripts/golden_case_check.py`：**是**。运行 `./verify.sh`：**是**。是否碰过 Golden 期望值：
  **否**。
- `inject_demo4_regression.sh`：注入成功。
- `verify.sh`（注入后）：`pytest` 出现 `4 failed, 15 passed`，退出码 1，**确定性 BLOCK**。
  与 Run 1 相同的情况：`set -e` 导致 pytest 失败后脚本没有跑到 `golden_case_check.py`，独立
  Golden 步骤这次也没有机会打印自己的 FAIL；阻断信号仍然确定、来自明确的业务断言失败。
- `restore_demo4_fixed.sh`：`verify.sh` 恢复到 `19 passed` + Golden 5 项全 PASS。
- 是否需要讲师补提示：**否**。

### 汇总

| Run | D4-2 读取事实报告 | D4-2 产出四类资产 | D4-2 耗时 | D4-3 自行发现规则 | D4-3 跑 verify.sh | D4-3 碰 Golden 值 | D4-3 耗时 | 注入→BLOCK | 恢复→PASS | 讲师补提示 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 是 | 是（规则/Golden/verify.sh/AGENTS） | 3m31s | 是 | 是 | 否 | 1m3s | 是（pytest 4 failed，Golden 步骤因 `set -e` 未执行） | 是 | 否 |
| 2 | 是 | 是（规则/Golden 作为 pytest 用例/verify.sh 未变逻辑/AGENTS） | 3m45s | 是 | 是 | 否 | 1m41s | 是（同一次 pytest 里 7 failed，含 3 条具名 Golden 用例） | 是 | 否 |
| 3 | 是 | 是（规则/独立 Golden 脚本/verify.sh 两步/AGENTS） | 4m10s | 是 | 是 | 否 | 1m25s | 是（pytest 4 failed，Golden 步骤因 `set -e` 未执行） | 是 | 否 |

**三次都无需讲师补提示，注入→BLOCK→恢复→PASS 三次全部确定性成立，D4-3 三次都在没有被
告知规则的情况下自己找到了规则文档和统一验证入口，也都没有触碰 Golden 期望值。**

### 已知风险（如实记录，不为报告好看而美化）

- `inject_demo4_regression.sh` 依赖的代码行（`export_rows = [... for row in eligible_rows]`）
  在三次真实沉淀会话之后都完好无损——scope-discipline 提示（"不要顺手重构"）目前有效，但样本
  只有 3 次，不构成长期保证；如果未来某次 live 会话仍然重命名或重构了这行代码，注入脚本会
  报错退出（"没有找到预期代码行"），不会静默失败或误判，讲师需要先跑
  `./scripts/restore_demo4_sedimented.sh` 兜底。
- 三次 D4-2 对"Golden Case"和"统一验证入口"的具体实现方式都不同（独立脚本 / pytest 目录 /
  两步 verify.sh），这是允许的（任务本身允许 Agent 自行组织），但其中两次（Run 1、Run 3）的
  `verify.sh` 用 `set -euo pipefail` 顺序执行两步，导致 pytest 先失败时 Golden 步骤根本没有
  运行、也就不会打印独立的 Golden 结果行。**阻断信号本身仍然确定**（非零退出码 + 具体失败的
  业务断言），但如果课堂现场想要看到和参考实现完全一致的
  `Export eligibility Golden Case: FAIL` / `OVERALL: BLOCKED` 字样，不能保证每次 live 沉淀
  都产出这种呈现方式；届时可以用 `./scripts/restore_demo4_sedimented.sh` 切到讲师参考实现
  （`instructor/baselines/demo4-sedimented/verify.sh`，两步都会跑完再报总状态）来保证这段
  措辞可复现。

## 补充：自动化回归（`scripts/acceptance_check.py`）

在真实 Agent 彩排之外，`scripts/acceptance_check.py` 里内置的 D4 链路检查
（reset → `restore_demo4_sedimented.sh` → `inject_demo4_regression.sh` → BLOCK →
`restore_demo4_fixed.sh` → PASS → reset）持续作为脚本级回归门禁保留，最近一次运行
（2026-09-14，本轮小修之后）：65 项检查全部 PASS，`OVERALL: PASS`，D0/D1/D3 不受影响。
这条自动化链路用讲师参考实现（`instructor/baselines/demo4-sedimented/`）跑，不依赖当次
live Agent 产出的资产组织方式，所以即使某次课堂 D4-2 的产出结构和参考实现不同，这条门禁
依然能独立验证"注入→BLOCK→恢复→PASS"这条链路本身没有坏。

## 幂等性

三次真实彩排前后，均以 `./scripts/reset_demo4.sh` 收尾；收尾后 `workspaces/demo4-sedimentation`
与 `instructor/baselines/demo4-sedimentation`（未沉淀起点）逐文件字节一致，仓库里没有残留任何
一次彩排产出的文件（`docs/rules/`、`golden/`、`scripts/golden_case_*.py`、
`tests/golden/` 等，均只存在于三次彩排各自的临时工作树状态里，reset 后清空）。
