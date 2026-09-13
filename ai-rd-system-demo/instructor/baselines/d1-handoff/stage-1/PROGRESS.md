# PROGRESS

> 本文件记录"这件事现在做到哪里"，每次 session 结束前更新。长期项目事实见 `PROJECT-MEMORY.md`；历史记录见 Git History。

## 状态：进行中（上一个 session 已结束，等待接手）

## 已完成

- [x] 客户名称筛选（模糊匹配），**后端行为 + 页面入口都已完成**
  - `app/financing/service.py::list_applications` 新增 `customer_name` 参数：在 `all_applications_for_user()`（权限过滤）之后、`paginate()` 之前做大小写不敏感的子串匹配。
  - `app/main.py` 暴露 `customer_name` query 参数，透传给 service。
  - `static/index.html` 增加客户名称输入框 + 筛选/清除按钮：查询时把输入框的值真实传给 `/api/financing-applications?customer_name=...`；翻页（上一页/下一页）时保留当前筛选条件；点击清除或切换筛选条件时回到第 1 页。
  - 测试：`tests/test_customer_filter.py`（命中、空结果、分页+权限组合三个用例，验证后端行为）；`tests/test_static_page.py`（验证页面存在客户名称筛选控件且真的把值传给 API，同时验证状态筛选和导出控件目前还不存在）。
  - 决策依据见 `DECISIONS.md` D-001、D-002、D-004。

## 未完成 / 下一步

- [ ] 融资状态筛选（精确匹配），需要能与客户名称筛选组合生效。**完成范围包括**：service/API 的 `status` 参数 **以及** `static/index.html` 里的状态筛选控件（能与客户名称筛选组合使用）。
- [ ] 导出接口：复用既有 `app/common/export_jobs.py` 的 `ExportQueue`；导出的必须是"当前筛选条件下的结果"，并携带发起用户的权限范围（tenant scope），不能导出用户无权限看到的数据。**完成范围包括**：导出 API **以及** `static/index.html` 里的导出入口——点击后要在页面上展示真实创建的导出任务结果（至少包含 job id、status、当前筛选条件中的关键信息），不能只是前端提示文字。
- [ ] 上述两项各自的"完成"标准见 `TASK.md`《功能完成定义》：后端行为 + 页面入口 + 对应开发侧测试，缺一不可；具体页面怎么实现（标签、交互方式、DOM 结构）不做规定，自行决定。
- [ ] 补充对应 pytest 用例（包含对页面改动的开发侧验证，参考 `tests/test_static_page.py` 的写法：读取 `static/index.html` 源码做结构性断言，不需要引入浏览器自动化依赖），并重新跑 `./verify.sh` 确认全绿

## 最近一次验证结果

`./verify.sh` 收尾时是全绿（7 passed：2 条 baseline 用例 + 3 条 customer_name 筛选用例 + 2 条页面结构用例）。接手后请先重新跑一遍，不要假设环境状态没变。
