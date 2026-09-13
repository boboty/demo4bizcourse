# Demo 资产验收清单

## 总体
- [ ] 四次都真正退出 PPT；Demo 1A 使用 CNN 可视化，1B/2/3/4 进入真实电脑操作。
- [ ] 同一个仓库，两条任务线；没有第四个业务细节。
- [ ] 每个 Demo 都能用一句承重判断收口。
- [ ] 所有操作有 reset / deterministic fallback。

## D1｜工程现场接力（主 demo）
- [ ] `workspaces/d1-handoff/` reset 后有且仅有 3 个 Git 提交，最后一条显式标记 session 已结束。
- [ ] Checkpoint 里 `feature-list.json` 显示客户名称筛选 `done`（含 `ui`），状态筛选/导出 `pending`；`./verify.sh` 全绿（7 passed）。
- [ ] **页面层**：`./scripts/d1_handoff_serve.sh` 启动后，浏览器打开接手起点页面能看到——客户名称筛选控件存在且真实生效；状态筛选控件和导出按钮都不存在。
- [ ] 课堂顺序是 D1-1（先看上一棒页面）→ D1-2（关掉上一棒）→ D1-3（新 Session 接手）→ D1-4（回浏览器看结果）→ D1-5（收口），不再以"先做五个预测"开场；五项预测保留作讲师 QA，可用 `scripts/d1_handoff_run.sh` 自动化复核。
- [ ] 全新 session 用 `codex exec --ephemeral`（或真正新开的交互会话），不携带任何历史聊天记录，且只从 `workspaces/d1-handoff` 内读取上下文。
- [ ] **页面层**：Fresh Session 完成后，浏览器刷新能看到——状态筛选生效、客户名称+状态组合筛选生效、导出按钮调用真实 `/api/financing-applications/export` 并在页面展示真实 job id/status/筛选条件。
- [ ] `instructor/d1/handoff/results/latest/result.json` 的 `predictions` 五项分别记录命中与否，不做一刀切 PASS/FAIL（讲师 QA 用，非课堂主画面）。
- [ ] `health_check_timing.ran_verify_or_pytest_before_first_edit`、`state_written_back`、`stayed_in_workspace` 均有记录。
- [ ] D1 不展示 Golden Case、独立 Validator 或规则沉淀资产；这些分别属于第三讲、第四讲。
- [ ] 预跑 `scripts/d1_handoff_prerun.sh` 结果见 `instructor/d1/handoff/PRERUN-REPORT.md`；3 次完整"reset→浏览器接手前→Fresh Session→浏览器接手后→verify.sh"链路见 `instructor/d1/handoff/UI-PRERUN-REPORT.md`；`scripts/d1_handoff_verify_setup.py` 为 `OVERALL: PASS`（含页面层检查）。
- [ ] `instructor/reference/d1-handoff-completed/`（fallback）页面本身具备客户筛选、状态筛选、导出三项可操作能力，`./scripts/d1_handoff_restore_fixed.sh` 恢复后浏览器刷新即可验证，不止是"测试全绿"。

## D1 补充实验｜Task → Plan → 项目环境 → 自检要求（Level 1/2/3）
- [ ] Level 1/2/3 都从同一个 `instructor/d1/task.txt` 和冻结融资 baseline 开始。
- [ ] Level 1 只有只读 Plan；Level 2 额外加载真实项目记忆和代码规范；Level 3 再加载开发侧自检要求。
- [ ] Level 1/2 不修改代码、不运行开发测试；Level 3 保存 Plan v3 后才执行真实开发任务。
- [ ] 每一级保存 Plan、trace、manifest；Level 3 还保存实际修改文件、Agent 主动测试、测试结果、diff 和自检结果。
- [ ] 课堂使用 `scripts/d1_compare.sh` 展示三级递进表和 Plan v1/v2/v3 可读 diff，不输出 winner 或把独立验收作为高潮。
- [ ] 任一级 Codex 超过默认 180 秒时结果标记为 `TIMEOUT`，trace、stderr、manifest、diff 和 elapsed 均保留。
- [ ] 只有三级 live 证据都完整时才运行 `scripts/d1_save_fallback.sh`；`scripts/d1_compare.sh saved` 必须明确显示 `SAVED_EVIDENCE`。

## Demo 1
- [ ] CNN 页面提前打开并验证可用。
- [ ] 准备 2–3 个容易产生歧义的数字写法。
- [ ] Codex 一句话任务无论“直接做 / 追问 / 做对”都能收口。
- [ ] 使用 `workspaces/demo12-financing/`，不在 workspace 预置一句话任务。

## Demo 2
- [ ] 五要素文字与课件 P37–41 一致。
- [ ] 与 Demo 1 使用同一个 `workspaces/demo12-financing/`、同一个 baseline、同一个 `AGENTS.md` 和同一个模型。
- [ ] 开发 Agent 只在该 workspace 运行开发侧 `pytest -q`，不读取独立验收脚本实现。
- [ ] 讲师退出 workspace 后，从仓库根目录运行 `.venv/bin/python instructor/checks/task_a_acceptance.py`，验收单条件、多条件、空结果、权限、异步导出、前端行为。
- [ ] 前端验收不绑定固定 HTML `id`、`class` 或变量名。
- [ ] 学员实战 25 分钟：5+12+5+3。

## Demo 3
- [ ] 在 `workspaces/demo3-developer/` 运行 `../../.venv/bin/python -m pytest -q` 和 `bin/self-check`，wrong state 全绿 / PASS（自检看不到导出规则）。
- [ ] developer 测试全绿后启动 `./scripts/demo3_serve.sh`，固定端口为 `127.0.0.1:8030`；浏览器三项功能都能点，REJECTED 仍可查询但会被错误导出。
- [ ] 在 `workspaces/demo3-validator/` 先形成 Independent Expectation，再运行 `../../.venv/bin/python bin/actual-output validation/cases.json`（或讲师自查用 `./scripts/demo3_validator.sh`）；wrong state 必须发现 BLOCKER。
- [ ] validator 的实际结果只来自 HTTP，不包含 developer 路径或实现模块名。
- [ ] GC-02（REJECTED）导出必须是 expected 0 vs actual 1；GC-03（混合结果）必须是 expected 只含 APPROVED/FUNDED vs actual 含全部状态。
- [ ] 验收角色在形成期望前看不到实现、开发测试和开发聊天。
- [ ] fixed state 下开发测试 + 黑盒实际输出与独立期望一致，且 REJECTED/SUBMITTED 仍能在列表查询中查到。

## Demo 4｜demo4-sedimentation（沿用 D1→D3 融资申请页面）
- [ ] `./scripts/reset_demo4.sh` 后是"D3 fixed"状态：开发测试 `19 passed`，浏览器 REJECTED 仍可查询、导出 0 条；还没有规则文档、`golden/` 或统一 `verify.sh`（此时 `verify.sh` 只跑 pytest）。
- [ ] D4-2 事故复盘任务不指定固定文件名，只要求覆盖四类资产：规则文档（进 repo、可发现、有 owner）、Golden Case（业务事实驱动、独立于开发单测）、统一 `verify.sh`（pytest + Golden 都从这里进）、可发现的工程记忆（`AGENTS.md` 指向前三者，不重复整份规则原文）。
- [ ] 讲师参考沉淀态：`instructor/baselines/demo4-sedimented/`（`docs/rules/export_eligibility.md` + `golden/cases.json` + `golden/check_export_eligibility.py` + 升级后的 `verify.sh` + `AGENTS.md`），`./scripts/restore_demo4_sedimented.sh` 可确定性恢复到这个目标状态。
- [ ] D4-3 全新 Session 只给一个普通维护任务（新增 `exported_by` 字段），不提 D3、不贴规则；应能自己发现规则文档、跑 `./verify.sh`、不修改 `golden/` 期望值。
- [ ] D4-4 `./scripts/inject_demo4_regression.sh` 确定性重新引入历史 bug（导出改回直接用 `rows`），不依赖模型犯错；浏览器 REJECTED 查询 1 条、导出也变成 1 条。
- [ ] D4-5 `(cd workspaces/demo4-sedimentation && ./verify.sh)` 必须确定性 `OVERALL: BLOCKED`，输出包含 `Export eligibility Golden Case: FAIL` 和 `GC-02 REJECTED`；没有人重新讲业务规则或人工判断。
- [ ] D4-6 `./scripts/restore_demo4_fixed.sh` 只恢复导出逻辑，不触碰沉淀资产；浏览器恢复导出 0 条，`./verify.sh` 回到 `OVERALL: PASS`。
- [ ] `scripts/acceptance_check.py` 覆盖完整链路（reset → 沉淀态 PASS → 注入 BLOCK → 恢复 PASS → reset）且可重复运行；旧 settlement/FX_LOSS 相关脚本与素材（`restore_demo4_before.sh`、`restore_demo4_learned.sh`、`instructor/golden/`、`instructor/baselines/demo4-learned/`）已删除。
