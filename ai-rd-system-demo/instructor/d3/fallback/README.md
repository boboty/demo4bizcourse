# D3 Fallback

这里是一次真实预跑的证据，不是模拟结果：`workspaces/demo3-developer` 从 `instructor/baselines/demo3-developer`（放款导出仍有 bug）重置开始，按 `../defect-report.md` 的缺陷单在同一个 workspace 里手工完成修复（未替换整个目录），再重新跑测试、自检和独立验收黑盒得到下面这些文件。

- `golden-before.txt` / `golden-after.txt`：独立验收在修复前后的输出（`scripts/demo3_validator.sh`）。
- `developer-tests-before.txt` / `developer-tests-after.txt`：开发侧 `pytest -q` 在修复前后的输出。
- `self-check-before.txt` / `self-check-after.txt`：`bin/self-check` 在修复前后的输出（注意修复前也是 PASS——自检本来就看不到导出规则）。
- `workspace.diff`：修复后的 `workspaces/demo3-developer` 相对 `instructor/baselines/demo3-developer` 的完整 diff。

课堂现场 live fix 失败或时间不够时，可以直接展示这些文件，或运行 `./scripts/restore_demo3_fixed.sh` 把 `workspaces/demo3-developer` 直接切到修复后状态（来自 `instructor/baselines/demo3-fixed`，与这里手工修复的结果等价）。
