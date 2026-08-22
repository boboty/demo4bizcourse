# Demo 2｜Codex 输入

从 `workspaces/demo2-five-elements/` 中把 `task-a-five-elements.md` 整份交给 Codex。

完成后至少展示：
1. 计划；
2. diff；
3. `pytest -q`；
4. 与 Demo 1 保存的 patch 并排比较。

开发 Agent 不读取或运行讲师 workspace 外的独立验收脚本。Codex 会话退出 Demo 2 workspace 后，由讲师在仓库根目录运行隐藏验收。
