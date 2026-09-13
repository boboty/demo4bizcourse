# 兜底录屏计划

建议每段都录，但优先级：D0 > Demo 3 > Demo 4 > Demo 2 > Demo 1B。

- D0：必须录"完整一次现场运行"，时长不限（真实链路约 1–3 分钟）。录屏必须包含
  `pytest -q` 的红灯输出、Agent 读取失败信息的那几秒、以及最后 `8 passed`。
  同一个 baseline、同一个任务文本、同一种运行方式；不要用另一个项目的录像顶替。
  除录屏外还要保留机器可读证据：`./scripts/d0_save_fallback.sh` 会把最近一次真实跑通
  的运行（trace.jsonl、workspace.diff、final.md、result.json）冻结到
  `instructor/d0/fallback/`，课堂超时时可直接展示。
- Demo 1A：网页本身可现场操作；额外录 60 秒备用。
- Demo 1B：录“Codex 接一句话任务”的一种正常分支。
- Demo 2：录完整五要素执行 + 验收脚本 PASS。
- Demo 3：必须录 8–10 分钟压缩版：开发测试全绿 → 独立验收 BLOCKER → 修复 → PASS。
- Demo 4：录复盘写 AGENTS.md → 关闭会话 → 新会话正确读取规则。

录屏中不要依赖讲师口播才能看懂；屏幕上保留命令和关键结果。
