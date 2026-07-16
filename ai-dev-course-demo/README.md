# AI 研发课程双 Demo 项目

这是《外部企业人工智能赋能研发》课程使用的本地 FastAPI 演示项目。两个课堂 Demo 共用同一套代码、任务包和验收标准。

当前基线能力包括用户列表分页、用户名与状态筛选、服务层、内存仓储、基础测试和可复用的 Excel 工具。`demo-baseline` 检查点刻意不包含用户导出接口，供现场从任务包开始演示。

## 快速开始

```bash
./scripts/setup.sh
./scripts/run.sh
./scripts/test.sh
```

服务默认监听 `http://127.0.0.1:8000`，OpenAPI 页面为 `http://127.0.0.1:8000/docs`。

## 已有接口

```text
GET /health
GET /api/users?page=1&page_size=20&username=ali&status=active
```

列表响应中的 `total` 是筛选后的总数，`items` 是当前页数据。用户名筛选不区分大小写并采用包含匹配，状态采用精确匹配。

## 演示重置

```bash
./scripts/reset_demo.sh
```

该命令只重置本 Demo 自己的 Git 仓库到 `demo-baseline`，并保留 `.venv`。执行前应保存需要保留的本地修改。

