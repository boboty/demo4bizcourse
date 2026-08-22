# API

## GET /api/financing-applications
参数：`page`、`page_size`、`customer_name`、`status`。请求头 `X-User` 保留既有数据权限。

## POST /api/financing-applications/export
参数：`customer_name`、`status`。使用已有异步导出任务通道，返回 202 与 job id。

## GET /api/export-jobs/{job_id}
查询已有异步导出任务。
