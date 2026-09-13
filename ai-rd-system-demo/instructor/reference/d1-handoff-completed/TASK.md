# TASK

> 给融资申请列表增加客户名称和融资状态筛选，并支持导出。

## 开发侧验收方向（不是独立验收标准，不含 Golden Case）

- 客户名称按模糊（子串）匹配；融资状态按精确匹配。
- 支持单条件、多条件组合筛选，以及空结果的处理。
- 筛选不能扩大 `PROJECT-MEMORY.md` 里已经建立的 tenant 数据权限范围。
- 导出复用既有的异步 `ExportQueue`（`app/common/export_jobs.py`），导出的必须是"当前筛选条件下的结果"，并携带发起用户的权限范围。

## 项目背景

- 长期工程事实见 `PROJECT-MEMORY.md`；长期代码规范见 `CODING-STANDARDS.md`。这两份文件不随任务进度变化，只在项目架构真正变化时更新。
- 当前任务进度见 `PROGRESS.md`；关键工程决策见 `DECISIONS.md`；功能级完成情况见 `feature-list.json`。
- 健康检查 / 验证方式：`./verify.sh`。
