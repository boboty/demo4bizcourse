# 融资申请与还款计划

放款业务的最小基础工程：融资申请列表（分页 + 数据权限）和还款计划生成。

```bash
../../.venv/bin/python -m pytest -q
../../.venv/bin/python -m uvicorn app.main:app --port 8000
```

模块：

- `app/financing/`：融资申请列表，按 `X-User` 做 tenant 权限过滤，复用 `app/common/pagination.py`。
- `app/repayment/`：还款计划，把放款金额按 `periods` 期均摊，通过 `/api/repayment-schedule` 暴露。
- `app/common/`：分页、权限、异步导出队列等公共模块。
