# Repository instructions

## Working agreements

- 修改尽量小而聚焦，不顺手重构无关代码。
- 除非任务明确要求，不新增第三方依赖。
- 修改 Python 后运行 `pytest -q`。
- 任务给出验收标准时，把验收标准视为交付契约的一部分。

## Workspace isolation

- `workspaces/demo1-vague/`、`demo2-five-elements/`、`demo3-developer/`、`demo3-validator/` 和 `demo4-sedimentation/` 是五个独立课堂工程根目录。
- Codex 课堂会话必须从目标 workspace 启动；不要从本仓库根目录开始任务。
- `instructor/` 是讲师资产区，包含 Runbook、验收脚本、Golden 和 reset 快照，不复制进学员 workspace。
