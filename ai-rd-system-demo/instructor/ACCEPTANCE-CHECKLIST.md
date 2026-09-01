# Demo 资产验收清单

## 总体
- [ ] 四次都真正退出 PPT；Demo 1A 使用 CNN 可视化，1B/2/3/4 进入真实电脑操作。
- [ ] 同一个仓库，两条任务线；没有第四个业务细节。
- [ ] 每个 Demo 都能用一句承重判断收口。
- [ ] 所有操作有 reset / deterministic fallback。

## D1｜同模型、同任务、两个 Harness
- [ ] 使用 `scripts/d1_run.sh a` 和 `scripts/d1_run.sh b`，两次只从同一个 `instructor/d1/task.txt` 读取任务。
- [ ] A/B 的 manifest 中模型、推理档位、任务哈希与数据哈希相同；两次均由 `reset_d1.sh` 从同一冻结 baseline 创建。
- [ ] A 使用 Responses API 且 `tools=[]`，只读 source bundle；B 使用原生 Codex Coding Harness，不复制 D1 helper 文件。
- [ ] A/B 工作区均不包含验收脚本、Golden、参考实现或边界白名单。
- [ ] 讲师使用 `scripts/d1_compare.sh` 展示统一轨迹、开发测试、独立验收与越界修改证据，不预设任一 Harness 的结果。

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
- [ ] 在 `workspaces/demo3-developer/` 运行 `../../.venv/bin/python -m pytest -q tests/test_settlement_developer.py`，wrong state 全绿。
- [ ] developer 测试全绿后启动 `./bin/start-blackbox`，固定端口为 `127.0.0.1:8765`。
- [ ] 在 `workspaces/demo3-validator/` 先形成 Independent Expectation，再运行 `../../.venv/bin/python bin/actual-output validation/cases.json`；wrong state 必须发现 BLOCKER。
- [ ] validator 的实际结果只来自 HTTP，不包含 developer 路径或实现模块名。
- [ ] GC-01 的差异必须是 6200 combined vs 5000 refund-only。
- [ ] 验收角色在形成期望前看不到实现、开发测试和开发聊天。
- [ ] fixed state 下开发测试 + 黑盒实际输出与独立期望一致。

## Demo 4
- [ ] 复盘新增的是规则与检查项，不是这次案例金额。
- [ ] 必须新开 Codex 会话验证规则加载。
- [ ] 新会话变体结果：FX_LOSS_PLUS_TAX_REFUND / 11000。
