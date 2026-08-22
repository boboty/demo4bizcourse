# 模糊提示真实隔离预跑记录

## 记录性质

以下是 2026-07-17 在 `demo-baseline` 临时 worktree 中真实调用 Codex CLI 的关键记录，不是课堂编写的模拟输出。完整 CLI 输出没有写入仓库；本文保留命令、会话、实际 diff、实际测试和停止原因。

## 输入与环境

```text
$ codex exec --ephemeral --sandbox workspace-write -m gpt-5.4 \
    -C <temporary-worktree> \
    '请根据当前项目，实现用户列表导出功能。'

OpenAI Codex v0.135.0
model: gpt-5.4
session id: <redacted-session-id>
baseline: d58c2c8
```

这里的 `d58c2c8` 是安全脚本修复前的原始预跑提交，作为真实执行证据保留；当前 `demo-baseline` 为 `9a5b0ac`，业务代码和基础测试状态不变。

默认模型的首次尝试因本机 CLI 版本不兼容退出；随后显式使用 `gpt-5.4` 完成了上述实际预跑。

## 实际改动摘要

```text
 README.md                    |  5 +++--
 app/api/users.py             | 31 +++++++++++++++++++++++----
 app/services/user_service.py | 27 ++++++++++++++++++++++++
 tests/test_user_service.py   | 44 ++++++++++++++++++++++++++++++++++++++
 tests/test_users_api.py      | 50 ++++++++++++++++++++++++++++++++++++++++++++
 5 files changed, 151 insertions(+), 6 deletions(-)
```

Codex 自行选择了 `/api/users/export`、复用 `UserService.search_users` 并处理了 null；但因为提示没有验收边界，它把列名写为“显示名”，没有实现或测试 10000 行上限，也没有给出超限行为。

## 实际验证结果

CLI 自己创建 `.venv` 后因隔离环境 DNS/缓存权限无法安装依赖，持续寻找离线环境。本次预跑在约四分钟后由执行者停止，CLI 退出码为 1；这部分不冒充一次完整通过的执行。

随后使用主项目已经安装好的同版本 Python 3.11 环境，对临时 worktree 的真实改动运行 pytest：

```text
.......F.......                                                          [100%]
FAILED tests/test_user_service.py::test_export_users_reuses_filters_and_serializes_nullable_fields
At index 2 diff: (..., None, ...) != (..., '', ...)
1 failed, 14 passed
```

失败原因是 openpyxl 写入空字符串后回读为空单元格值 `None`，而模糊提示预跑生成的测试断言为 `""`。

## 课堂整理结论

这一段是基于上述真实结果的讲解摘要，不是原始 CLI 输出：模糊提示也可能生成“看起来完整”的接口和测试，但没有事先定义列名、数量上限与验收语义，就无法判断这些自选行为是否真正完成业务任务。
