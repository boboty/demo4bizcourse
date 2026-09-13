# PROGRESS

> 本文件记录"这件事现在做到哪里"，每次 session 结束前更新。长期项目事实见 `PROJECT-MEMORY.md`；历史记录见 Git History。

## 状态：进行中（上一个 session 已结束，等待接手）

## 已完成

- [x] 客户名称筛选（模糊匹配）
  - `app/financing/service.py::list_applications` 新增 `customer_name` 参数：在 `all_applications_for_user()`（权限过滤）之后、`paginate()` 之前做大小写不敏感的子串匹配。
  - `app/main.py` 暴露 `customer_name` query 参数，透传给 service。
  - 测试：`tests/test_customer_filter.py`（命中、空结果、分页+权限组合三个用例）。
  - 决策依据见 `DECISIONS.md` D-001、D-002。

## 未完成 / 下一步

- [ ] 融资状态筛选（精确匹配），需要能与客户名称筛选组合生效
- [ ] 导出接口：复用既有 `app/common/export_jobs.py` 的 `ExportQueue`；导出的必须是"当前筛选条件下的结果"，并携带发起用户的权限范围（tenant scope），不能导出用户无权限看到的数据
- [ ] 上述两项完成后，补充对应 pytest 用例，并重新跑 `./verify.sh` 确认全绿

## 最近一次验证结果

`./verify.sh` 收尾时是全绿（5 passed：2 条 baseline 用例 + 3 条 customer_name 筛选用例）。接手后请先重新跑一遍，不要假设环境状态没变。
