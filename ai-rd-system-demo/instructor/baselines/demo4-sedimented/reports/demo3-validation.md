# D3 独立验收报告｜放款处理导出资格

独立验收角色：`workspaces/demo3-validator`（与开发实现隔离，只通过黑盒 HTTP 验证）。
业务事实源：`rules/export_eligibility_source_of_truth.md`、`rules/tenant_access_source_of_truth.md`（均在验收角色的 workspace 内，开发方当时看不到）。

## 第一次验收（开发方修复前）

```
Developer tests: 13 passed（开发方自报，全绿）
Developer self-check: SELF-CHECK: PASS（自检清单没有"哪些状态允许放款导出"这一条，看不到这条规则）

Golden validation:
GC-01 APPROVED       PASS
GC-02 REJECTED       FAIL   export expected 0 ids=[], actual 1 ids=['FA-1004']
GC-03 MIXED          FAIL   export expected 3 ids=['FA-1002', 'FA-1003', 'FA-1005'], actual 5 ids=['FA-1001', 'FA-1002', 'FA-1003', 'FA-1004', 'FA-1005']
GC-04 TENANT_SCOPE   FAIL   export expected 2 ids=['FA-2001', 'FA-2003'], actual 3 ids=['FA-2001', 'FA-2002', 'FA-2003']

Overall: BLOCKER
Root cause classification: 条件遗漏——开发方第一次实现和自检时没有见过独立业务事实源里的放款
处理导出资格规则，导出逻辑直接复用了查询结果，没有单独做状态过滤。
Recommended fix: 在放款处理导出（不是列表查询）里增加一层"允许导出状态"过滤，只允许
APPROVED / FUNDED；SUBMITTED / REJECTED 仍必须可以在列表查询里查到。
```

## 修复后复验

开发方收到独立验收发现后修复了 `app/financing/service.py` 的导出逻辑（新增
`EXPORT_ELIGIBLE_STATUSES` 过滤），并补充了 `tests/test_export_eligibility.py`（6 条新增测试）。

```
Developer tests: 19 passed（13 条原有 + 6 条新增）

Golden validation:
GC-01 APPROVED       PASS
GC-02 REJECTED       PASS
GC-03 MIXED          PASS
GC-04 TENANT_SCOPE   PASS

Overall: PASS
Root cause classification: 业务条件遗漏导致的实现错误；根因是独立业务事实未进入开发上下文，开发实现与测试共享不完整理解。
```

## 已经通过独立验收确认的事实（供后续沉淀引用）

- 放款处理导出（`POST /api/financing-applications/export`）只允许 `APPROVED`、`FUNDED` 两种状态进入导出结果。
- `SUBMITTED`、`REJECTED` 仍然必须能在列表查询（`GET /api/financing-applications`）里正常查到，这条规则不影响查询，只影响导出。
- 不指定状态筛选（混合结果）时，导出也只能保留 `APPROVED`/`FUNDED`。
- 这条规则不能改变既有的 tenant 数据权限范围（`GC-04`：bob 的导出结果里不能出现他看不到的 tenant，也不能因为状态规则而多导出本该被状态规则拦下的记录）。

这份报告只是这次事故已经被独立验证过的事实记录，不是项目级规则资产本身——它还没有被沉淀成
`docs/rules/`、Golden Case 或统一验证入口这类下一次可以直接复用的工程资产。
