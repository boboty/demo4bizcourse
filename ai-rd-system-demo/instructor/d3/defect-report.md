# Demo 3｜交给 Developer Agent 的缺陷单

独立验收发现一个 BLOCKER，请修复当前实现（`workspaces/demo3-developer`）和开发侧测试。

业务规则（放款处理导出规则，来自独立业务事实源）：

- 放款处理导出（`POST /api/financing-applications/export`）只允许 `APPROVED`、`FUNDED` 两种状态进入导出结果。
- `SUBMITTED`、`REJECTED` 仍然必须能在列表查询（`GET /api/financing-applications`）里正常查到，这条规则不影响查询，只影响导出。
- 不指定状态筛选时（混合结果），导出也只能保留 `APPROVED`/`FUNDED`。
- 这条规则不能改变既有的 tenant 数据权限范围。

独立验收发现：

```
GC-02 REJECTED      FAIL   export expected 0 ids=[], actual 1 ids=['FA-1004']
GC-03 MIXED         FAIL   export expected 3 ids=['FA-1002', 'FA-1003', 'FA-1005'], actual 5 ids=['FA-1001', 'FA-1002', 'FA-1003', 'FA-1004', 'FA-1005']
GC-04 TENANT_SCOPE  FAIL   export expected 2 ids=['FA-2001', 'FA-2003'], actual 3 ids=['FA-2001', 'FA-2002', 'FA-2003']
```

请：

1. 检查当前实现为什么会把不允许的状态导出。
2. 只修改"放款导出"的 eligibility，不要修改列表查询的行为，不要在前端隐藏按钮来绕过后端规则。
3. 保留 customer_name / status 组合筛选，保留 tenant scope。
4. 补充开发侧测试覆盖：REJECTED/SUBMITTED 仍可查询但导出为空；混合导出只保留 APPROVED/FUNDED；tenant 权限与状态规则同时成立。
5. 运行 `../../.venv/bin/python -m pytest -q`，全部通过。
6. 汇报修改和测试结果。
