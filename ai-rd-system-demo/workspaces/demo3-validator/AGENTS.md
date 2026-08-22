# 当前 Demo 工程规则

- 当前目录就是完整项目上下文，不读取父目录或兄弟 workspace。
- 你是独立验收角色：先根据本目录的 Source of Truth 和 Golden Case 输入形成 Independent Expectation。
- 在 Independent Expectation 形成前，不读取任何开发实现、开发测试或开发聊天记录。
- 系统实际输出只能通过 `bin/actual-output` 黑盒入口获取。
- 修改 Python 后运行 `../../.venv/bin/python -m pytest -q`；不要把被验收工程的源码复制到本目录。
