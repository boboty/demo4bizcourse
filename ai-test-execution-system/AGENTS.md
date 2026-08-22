# Runtime output policy

任何新增 runtime output 目录都必须在实现或文档中同时声明 Git policy：

- `track`：可审查的稳定代码或契约资产；
- `sample-only`：完全脱敏、固定的课堂样例；
- `ignore`：运行日志、截图、设备信息、执行 evidence、历史运行记录。

默认规则：运行日志、截图、设备信息、执行 evidence、历史运行记录均使用 `ignore`，不得提交真实运行原始产物。
