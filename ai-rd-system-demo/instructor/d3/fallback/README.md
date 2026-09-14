# D3 Fallback

这里是一次真实预跑的证据，不是模拟结果。全部文件由仓库里现有的脚本真实跑出来，可以用
下面这组命令重新生成一次（Golden label 中文化之后重新跑过一次，不是手工修改旧结果）：

```bash
./scripts/reset_demo3_developer.sh                 # 起点：instructor/baselines/demo3-developer（放款导出仍有 bug）
./scripts/demo3_serve.sh                           # 另开终端，8030
./scripts/demo3_validator.sh http://127.0.0.1:8030 # → golden-before.txt 的原始输出
./scripts/restore_demo3_fixed.sh                   # 切到修复后状态（instructor/baselines/demo3-fixed）
./scripts/demo3_save_fallback.sh http://127.0.0.1:8030
```

- `golden-before.txt` / `golden-after.txt`：独立验收（`scripts/demo3_validator.sh`）在修复前
  后的真实输出。修复前 `GC-02 未通过 FAIL`、`Overall: BLOCKER`；修复后四项中文 label 全 PASS。
- `developer-tests-before.txt` / `developer-tests-after.txt`：开发侧 `pytest -q` 在修复前后的输出。
- `self-check-before.txt` / `self-check-after.txt`：`bin/self-check` 在修复前后的输出
  （注意修复前也是 PASS——自检本来就看不到导出规则）。
- `workspace.diff`：修复后的 `workspaces/demo3-developer` 相对
  `instructor/baselines/demo3-developer` 的完整 diff（含新增的
  `tests/test_export_eligibility.py`）。

课堂现场 live fix 失败或时间不够时，可以直接展示这些文件，或运行
`./scripts/restore_demo3_fixed.sh` 把 `workspaces/demo3-developer` 直接切到修复后状态
（来自 `instructor/baselines/demo3-fixed`，与这里的 `workspace.diff` 描述的是同一份修复）。
