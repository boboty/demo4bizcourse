# 项目记忆｜融资申请基础工程

以下内容来自冻结 baseline 的实际代码，供 Level 2/3 使用，不是本任务的验收答案。

- `app/financing/repository.py` 通过 `X-User` 对应的 tenant 集合先筛出用户可见数据；当前权限边界在数据进入 service 前建立。
- `app/financing/service.py` 是融资申请列表的业务处理层，目前只负责取授权数据并调用 `paginate`。
- `app/common/pagination.py` 提供统一分页契约：`page` 从 1 开始，`page_size` 为 1–100，响应包含 `items`、`page`、`page_size`、`total`。
- `app/common/export_jobs.py` 已有内存 `ExportQueue` 和 `ExportJob`。baseline 尚未暴露融资申请导出 HTTP 路由；如果实现导出，应先研究并复用这个既有队列。
- `app/main.py` 是 FastAPI API 层，负责路由、请求参数、header 和 HTTP 错误协议；静态页面在 `static/index.html`。
- baseline 测试位于 `tests/test_financing_baseline.py`，目前覆盖数据权限和既有分页契约。
- 工程是 Python 3.12 + FastAPI + pytest；仓库已提供依赖，不因本任务引入新第三方包。

实施时要把这些事实转成计划中的项目决策；如果代码事实与记忆不一致，以实际代码为准并在完成说明中指出。
