# PROGRESS

> 本文件记录"这件事现在做到哪里"，每次 session 结束前更新。长期项目事实见 `PROJECT-MEMORY.md`；历史记录见 Git History。

## 状态：已完成

## 已完成

- [x] 客户名称筛选（模糊匹配）——`app/financing/service.py`、`app/main.py`、`tests/test_customer_filter.py`
- [x] 融资状态筛选（精确匹配，可与客户名称组合）——`app/financing/service.py::_filter_by_status`、`tests/test_status_filter_and_export.py`
- [x] 导出当前筛选结果（复用既有 `ExportQueue`，保留权限范围）——`app/financing/service.py::export_applications`、`app/main.py::export_financing_applications`、`tests/test_status_filter_and_export.py`

## 未完成 / 下一步

（无——本任务范围内的三项功能均已完成并有测试覆盖）

## 最近一次验证结果

`./verify.sh` 全绿（10 passed）。
