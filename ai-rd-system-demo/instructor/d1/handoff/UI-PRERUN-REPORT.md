# D1 工程现场接力｜页面层完整课堂链路预跑报告

> 与 `PRERUN-REPORT.md`（10 次、只跑 `d1_handoff_run.sh` 自动化脚本、只统计五项预测命中率）不同，本报告验证的是这次新增的产品线：
> **reset → 浏览器确认接手前页面 → 全新 Session 接手 → 完成 → 浏览器确认接手后页面 → `./verify.sh`**。
> 每次都是真实的 `reset_d1_handoff.sh` + 全新、无历史记忆的 Agent（只收到 `instructor/d1/handoff/prompts/handoff.md` 里那一句接手指令 + workspace 路径）+ 真实起服务 + 真实浏览器点击，不是模拟结果。

- 预跑次数：3
- 完整链路成功（COMPLETED）：3/3
- 是否需要人工追加"记得改 UI"之类的提示：0/3（三次都不需要）

## 逐次明细

| run | 接手前页面（浏览器确认） | Fresh Session 恢复坐标 | 是否主动做页面层 | 接手后页面（浏览器确认） | 耗时 | 人工追加提示 |
| --- | --- | --- | --- | --- | --- | --- |
| run-01 | 客户筛选 ✓ / 状态筛选 ✗ / 导出 ✗，客户名称筛选实测生效（"晨海"→2 条） | 正确：读 TASK/PROGRESS/DECISIONS/feature-list，先跑 `./verify.sh`（7 passed）再动手 | 是，未提示，主动实现 `#status-select` + `#export-btn` 并接到真实 API | 客户筛选 ✓ / 状态筛选 ✓ / 导出 ✓；"晨海"+APPROVED 组合筛选命中 FA-1005；导出显示真实 job id / QUEUED / 筛选条件 | 355.5s | 无 |
| run-02 | 同上（每次 reset 起点一致） | 正确：核对文档与代码事实一致后才动手，先跑 `./verify.sh`（7 passed） | 是，未提示，且自行起了临时 dev server 做了一轮浏览器自测后关闭 | 状态筛选（REJECTED→FA-1004）、导出结果（job id / QUEUED / 命中 1 条）实测正确；服务端口无残留 | 435.2s | 无 |
| run-03 | 同上 | 正确：明确点出"下一步是状态筛选+导出，两项都要后端+页面+测试" | 是，未提示，页面文案自行选择（"导出当前结果"而非"导出当前筛选结果"，属于允许的自由实现） | 组合筛选（北辰+FUNDED→0 条）、导出空结果（共 0 条）均正确；边界情况处理正确 | 349.7s | 无 |

## 观察

- 3 次的"接手前"页面截图完全一致：客户名称筛选可用，状态筛选和导出控件不存在——`reset_d1_handoff.sh` 生成的 checkpoint 是确定性的。
- 3 个 Fresh Session 都没有被提示"页面也要做"，均从 `TASK.md`《功能完成定义》和 `PROGRESS.md`/`feature-list.json` 里的"requires: ui"自己读出这个要求，并在最终页面里可操作、可验证。
- 3 次的开发侧测试数量不同（20 / 19 / 16 passed），但都覆盖了：状态精确匹配、与客户名称组合、空结果、tenant 权限不泄漏、导出复用 `ExportQueue`——说明"功能完成定义"约束的是范围，没有约束具体实现，三次给出的 UI 细节（按钮文案、导出结果展示位置）也确有差异，符合"不规定具体实现方式"的设计意图。
- 讲师用浏览器实测的筛选/导出结果，与 Fresh Session 自己声称完成的结果一致，没有出现"测试全绿但页面用不了"的情况。

## 复现方式

```bash
./scripts/reset_d1_handoff.sh
./scripts/d1_handoff_serve.sh &      # 另一个终端也可以
# 打开 http://127.0.0.1:8010/ 确认接手前页面
# 新开一个全新 Agent 会话，工作目录 workspaces/d1-handoff，只发 instructor/d1/handoff/prompts/handoff.md 里那一句
# 完成后刷新浏览器，验证状态筛选 / 组合筛选 / 导出
cd workspaces/d1-handoff && ../../.venv/bin/python -m pytest -q
```
