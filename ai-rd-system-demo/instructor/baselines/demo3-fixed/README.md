# Demo 3｜修复后状态（fallback / restore-fixed 用）

这是独立验收发现 BLOCKER、开发方按放款处理导出规则修复之后的目标状态：列表查询仍能查到 `SUBMITTED`/`REJECTED`，放款导出只保留 `APPROVED`/`FUNDED`，新增 `tests/test_export_eligibility.py` 覆盖修复后的行为。`scripts/demo3_restore_fixed.sh` 会把这份状态同步进 `workspaces/demo3-developer`，供课堂 fallback 或复验使用。

```bash
../../.venv/bin/python -m pytest -q
./verify.sh
./bin/self-check
```

浏览器查看（另起终端，保持运行）：

```bash
../../.venv/bin/python -m uvicorn app.main:app --reload --port 8030
```

打开 http://127.0.0.1:8030/ ，客户名称筛选、融资状态筛选、导出三项都能实际点用。
