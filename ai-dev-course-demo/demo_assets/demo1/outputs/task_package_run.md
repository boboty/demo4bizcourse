# 完整任务包真实执行记录

## 记录性质

本文件整理本轮 Codex 在主项目中执行完整附件任务的真实提交和终端证据。当前环境没有把完整 Codex 会话原文导出到仓库，因此以下“提交号、命令输出、耗时”是实际记录，“节点说明”是为课堂阅读整理的摘要，两者不混写为原始会话。

## 实际执行链路

```text
d58c2c8 chore: create course demo baseline
53e51ed feat: add initial user export
d272e2c test: add user export acceptance coverage
2749440 fix: export null display names as blank
```

以上提交号是安全脚本修复前的原始预跑记录，不做追溯改写。当前课堂标签按相同业务代码和测试状态映射为：`9a5b0ac` → `4c30224` → `4f269ee` → `4e4f92c`；每个检查点只额外统一了安装、重置和恢复脚本。

基线验证：

```text
$ time ./scripts/test.sh
11 passed in 0.16s
real 1.50
```

生成验收测试后的首次全量验证：

```text
$ time ./scripts/test.sh
AttributeError: 'NoneType' object has no attribute 'strip'
1 failed, 17 passed in 0.36s
real 0.73
```

根据失败做一行边界修复并补接口测试后：

```text
$ ./scripts/test.sh tests/test_user_export_service.py::test_null_display_name_is_mapped_to_empty_string tests/test_user_export_api.py::test_null_display_name_is_an_empty_excel_cell
2 passed in 0.01s

$ time ./scripts/test.sh
19 passed in 0.36s
real 0.74
```

## 课堂整理摘要

1. 读取项目：定位 `AGENTS.md`、列表路由、`UserService.search_users` 与现有 Excel helper。
2. 制定计划：把实现、验收测试、失败反馈和全量回归设为可验证步骤。
3. 修改代码：新增导出路由与服务，明确 10000 行返回 HTTP 422。
4. 生成测试：覆盖中文表头、空结果、筛选一致性、null 和数量边界。
5. 读取失败：新增测试真实暴露 `None.strip()`。
6. 修复重跑：只在导出映射边界把 null 转为空字符串，全量转绿。
7. 输出说明：用提交、测试和限制说明接入评审与审计。

更完整的真实原始失败/通过摘要位于 `demo_assets/demo2/logs/`，七节点讲师材料位于 `demo_assets/demo2/nodes/`。
