# D4 预跑报告

三次完整链路预跑，均在同一次小修（补新版 D3 验收报告 / 清理 service.py 里的旧引用 / 加
scope-discipline / 3 次预跑）之后执行。链路含义：`reset_demo4.sh`（回到 D3 fixed、未沉淀
起点）→ `restore_demo4_sedimented.sh`（切到"资产沉淀已完成"目标状态，`verify.sh` PASS）→
`inject_demo4_regression.sh`（确定性重新引入历史 bug）→ `verify.sh` 确定性 BLOCKED → 
`restore_demo4_fixed.sh`（只恢复导出逻辑）→ `verify.sh` 再次 PASS → `reset_demo4.sh`（收尾，
保证可重复运行）。

三次全部由 `scripts/acceptance_check.py` 自动跑完这条链路（含 D0/D1/D3 的既有检查），
外加一次针对第二轮的人工真实浏览器复核。

## Run 1（自动化）

- 开始：2026-09-14 06:49:42　结束：2026-09-14 06:49:49　耗时：7s
- 检查项：65 PASS / 0 BLOCKER
- 结果：`OVERALL: PASS`

## Run 2（自动化 + 人工真实浏览器复核）

- 自动化部分：开始 2026-09-14 06:49:49　结束 2026-09-14 06:49:57　耗时：8s，65 PASS / 0 BLOCKER，`OVERALL: PASS`。
- 人工浏览器复核（`http://127.0.0.1:8050/`，通过 Claude Browser 工具实测，非模拟）：
  1. `reset_demo4.sh` 后 `pytest -q` → `19 passed`；`restore_demo4_sedimented.sh` → `verify.sh` `OVERALL: PASS`。
  2. 浏览器：状态筛选 REJECTED → 列表 1 条；点"放款处理导出" → **共 0 条记录（当前筛选状态不满足放款导出条件，无可导出记录）**。
  3. `inject_demo4_regression.sh` → 重启页面服务 → 浏览器同样操作：列表仍 1 条，导出变成 **共 1 条记录**（历史 bug 复现）。
  4. `(cd workspaces/demo4-sedimentation && ./verify.sh)` → 确定性 `OVERALL: BLOCKED`，`Export eligibility Golden Case: FAIL`，`GC-02 REJECTED FAIL export expected rows: 0 ids=[], actual: 1 ids=['FA-1004']`；pytest 同时 `4 failed, 15 passed`。
  5. `restore_demo4_fixed.sh` → `verify.sh` `OVERALL: PASS`（Golden Case 全 PASS）→ 重启页面服务 → 浏览器：导出恢复 **共 0 条记录**，REJECTED 仍可查询。
- 结论：产品线（浏览器）和工程线（`verify.sh`）在注入前、注入后、恢复后三个时间点完全一致，没有出现"脚本说 BLOCK 但页面看起来正常"或反过来的情况。

## Run 3（自动化）

- 开始：2026-09-14 06:49:57　结束：2026-09-14 06:50:04　耗时：7s
- 检查项：65 PASS / 0 BLOCKER
- 结果：`OVERALL: PASS`

## 幂等性

三次运行前后，`workspaces/demo4-sedimentation` 与 `instructor/baselines/demo4-sedimentation`
（未沉淀起点）逐文件字节一致；重复运行 `scripts/acceptance_check.py` 不依赖上一次运行遗留的
状态，也不会在仓库里累积课堂运行痕迹（`instructor/d4/fallback/` 除外，那是显式调用
`demo4_save_fallback.sh` 才会写入的兜底证据，不是每次预跑自动产生的）。
