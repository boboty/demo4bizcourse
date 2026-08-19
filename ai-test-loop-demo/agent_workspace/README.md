# 课堂 Agent 工作区

本目录是课堂现场另一个 Codex Agent 的**私有工作区**。它应在这里生成：

- 自己设计的接口测试代码（如 `test_orders.py`）
- `test-report.md`：测试执行结果
- `bug-report.md`：发现的 Bug、证据与初步定位
- `evidence/`：截图 / 原始响应等证据文件

约束：

- 只在本目录内新增/修改文件；不要改动 `app/`、`docs/business-rules.md` 等被测与业务资料；
- 业务判断以 `docs/business-rules.md` 为唯一依据；
- 接口定义以 FastAPI 自动生成的 OpenAPI（`/openapi.json`）和 `api/openapi.yaml` 为准。

课前/课后由讲师执行 `python scripts/reset_demo.py` 清空本目录（保留本 README），
以便反复演示。
