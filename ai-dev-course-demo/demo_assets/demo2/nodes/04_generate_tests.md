# 节点 4：生成测试

> 资产状态：内容来自真实验收测试提交；对应截图尚未采集。

## 关键终端日志

```text
$ git show -s --oneline demo-validation-failed
4f269ee test: add user export acceptance coverage

$ git show --stat --oneline demo-validation-failed
 tests/test_user_export_api.py     | 52 +++++++++++++++++++++++++++++++++++++
 tests/test_user_export_service.py | 54 +++++++++++++++++++++++++++++++++++++++
 2 files changed, 106 insertions(+)
```

## 截图建议范围

待采集。画面显示两个新增测试文件和具有业务含义的测试名，至少包含 null 显示名称、空列表、中文表头、筛选一致性、恰好 10000 行和超过上限六类断言。

## 讲师应观察的证据

- 测试直接对应任务包中的可检查验收项，而不是只测 HTTP 200。
- `test_null_display_name_is_mapped_to_empty_string` 首次覆盖了既有测试遗漏的 null 分支。
- 接口测试通过解读工作簿核对中文表头、空结果和列表筛选口径。
- 数量上限同时覆盖允许 10000 行和拒绝 10001 行的边界。

## 一句讲解提示

测试把自然语言验收标准变成了机器可以重复执行的检查。
