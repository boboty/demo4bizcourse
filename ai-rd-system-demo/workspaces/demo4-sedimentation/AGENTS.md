# 当前 Demo 工程规则

- 当前目录就是完整项目上下文，不读取父目录或兄弟 workspace。
- 本工程使用 Python 3.11+ 和 pytest；不引入新的第三方依赖。
- 修改 Python 后运行 `pytest -q`，保持既有业务规则和测试契约。
- 课堂复盘角色可以把可复用的验证规则写入本文件和 `validation/checklist.md`。
