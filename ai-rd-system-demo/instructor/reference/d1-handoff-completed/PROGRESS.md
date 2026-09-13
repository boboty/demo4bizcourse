# PROGRESS

> 本文件记录"这件事现在做到哪里"，每次 session 结束前更新。长期项目事实见 `PROJECT-MEMORY.md`；历史记录见 Git History。

## 状态：已完成

## 已完成

- [x] 客户名称筛选（模糊匹配），**后端 + 页面均已完成**——`app/financing/service.py`、`app/main.py`、`static/index.html`（客户名称输入框 + 筛选/清除按钮）、`tests/test_customer_filter.py`、`tests/test_static_page.py`
- [x] 融资状态筛选（精确匹配，可与客户名称组合），**后端 + 页面均已完成**——`app/financing/service.py::_filter_by_status`、`static/index.html`（状态下拉框，与客户名称筛选共用同一次查询）、`tests/test_status_filter_and_export.py`、`tests/test_static_page.py`
- [x] 导出当前筛选结果（复用既有 `ExportQueue`，保留权限范围），**后端 + 页面均已完成**——`app/financing/service.py::export_applications`、`app/main.py::export_financing_applications`、`static/index.html`（导出按钮，把真实返回的 job id / status / 筛选条件 / 行数渲染到页面）、`tests/test_status_filter_and_export.py`、`tests/test_static_page.py`

## 未完成 / 下一步

（无——本任务范围内的三项功能均已完成，后端行为、页面入口和对应测试都有覆盖，见 `TASK.md`《功能完成定义》）

## 最近一次验证结果

`./verify.sh` 全绿（13 passed：2 条 baseline + 3 条客户名称筛选 + 5 条状态筛选/导出 + 3 条页面结构用例）。
