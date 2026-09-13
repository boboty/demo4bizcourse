# 开发侧自检清单

这是开发完成前的自检依据，不是独立验收标准，不包含 Golden Case 或外部 Source of Truth。自检只能证明"实现符合本工程自己的理解"，不能证明"业务理解本身是对的"。

1. 运行 `../../.venv/bin/python -m pytest -q`，全部通过。
2. 客户名称筛选（模糊匹配）、融资状态筛选（精确匹配）、组合筛选都按预期工作，空结果也有覆盖。
3. 数据权限仍由 `X-User` 和 tenant scope 控制（`app/common/security.py`），筛选和导出都不能绕过它。
4. 导出复用既有的异步 `ExportQueue`（`app/common/export_jobs.py`），导出的是"当前筛选条件下的结果"，并携带发起用户的权限范围（`tenant_scope`）。
5. 页面（`static/index.html`）三个功能都有真实入口：客户名称输入框、状态下拉框、导出按钮；导出结果展示的是后端真实返回的 job id / status / 记录数，不是前端写死的文案。
6. `git diff --stat` 确认修改边界只服务于本任务。

全部满足即可在完成报告中给出 `SELF-CHECK: PASS`。
