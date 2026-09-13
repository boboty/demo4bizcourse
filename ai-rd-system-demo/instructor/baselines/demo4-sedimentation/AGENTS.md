# 当前 Demo 工程规则

- 当前目录就是完整项目上下文，不读取父目录或兄弟 workspace，也不要在仓库里寻找课堂材料。
- 本工程统一使用 Python 3.12 和 pytest；不引入新的第三方依赖。
- 修改 Python 后运行 `../../.venv/bin/python -m pytest -q`（或 `./verify.sh`）。
- 当前状态：D3 独立验收发现并修复了一次放款处理导出资格问题（不允许的状态被一起导出）；
  修复已经落进 `app/financing/service.py` 和 `tests/test_export_eligibility.py`，业务行为正确、
  开发测试全绿。独立验收的完整事实记录在 `reports/demo3-validation.md`。这份文件目前还没有
  记录这次修复背后的规则、独立验证方式或统一验证入口——那正是这次任务要做的事。
