# 代码规范｜融资申请基础工程

以下规范是从冻结 baseline 的分层和已有测试整理出的项目级约定：

- API 层（`app/main.py`）负责请求参数、header、状态码和 HTTP 协议；不要把筛选业务堆在路由之外的协议分支里。
- 融资申请筛选逻辑进入既有 `app/financing/service.py`，并在既有 repository 权限范围之后处理。
- 优先复用 `app/common/pagination.py` 和 `app/common/export_jobs.py`，保持已有模块的接口语义。
- 保持现有分页响应结构和权限行为兼容；筛选不能扩大用户可见的 tenant 范围。
- 使用项目已有 Python/FastAPI/pytest 能力，不引入新的第三方依赖。
- 只修改完成本任务需要的文件；不做无关重构，不把任务文本、课堂资料或独立验收脚本复制进 workspace。
- 需求没有明确的业务边界时，在计划中写出假设和待确认事项，不把临场猜测伪装成项目规则。
- 每个筛选/导出 feature 必须同时有页面入口（`static/index.html`），不能只做 API；页面实现方式自定，但要是用户真能点、真能用的控件，不是摆设。
- 验证页面改动时复用已有手段：pytest 读取 `static/index.html` 源码做结构性断言（有没有某个控件、有没有把参数传给某个 API），或者用 `TestClient` 验证对应 API 行为；不引入浏览器自动化（Selenium/Playwright 等）依赖。
