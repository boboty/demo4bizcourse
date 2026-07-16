# 节点 3：修改代码

> 资产状态：内容来自真实首次实现提交；对应截图尚未采集。

## 关键终端日志

```text
$ git show -s --oneline demo-initial-implementation
4c30224 feat: add initial user export

$ git show --stat --oneline demo-initial-implementation
 app/api/users.py                    | 29 ++++++++++++++++++++--
 app/main.py                         |  6 +++--
 app/services/user_export_service.py | 48 +++++++++++++++++++++++++++++++++++++
 3 files changed, 79 insertions(+), 4 deletions(-)
```

## 截图建议范围

待采集。截取 Codex 修改摘要和核心 diff，重点显示新增导出路由、`UserExportService` 调用 `search_users`、中文表头及 `MAX_EXPORT_ROWS = 10_000`；避免只截最终文件而丢失修改过程。

## 讲师应观察的证据

- 首次实现只改动接口注册、用户接口和新导出服务三个相关文件。
- 导出服务复用原有搜索服务，并明确选择“超过 10000 行时拒绝”。
- Excel 表头顺序为用户ID、用户名、显示名称、邮箱、状态、创建时间。
- 此时只是“完成首次实现”，还没有测试证据证明任务已经完成。

## 一句讲解提示

代码变更只是闭环中的一个节点，接下来要用任务包里的验收条件检验它。
