# D0 workspace rule

- 当前目录就是本次 D0 的完整项目上下文，不读取父目录或兄弟 workspace。
- 只在当前 workspace 内检查和修改文件。
- 工程统一使用仓库根目录的 `.venv`：`../../.venv/bin/python -m pytest -q`。
