# 当前 Demo 工程规则

- 当前目录就是完整项目上下文，不读取父目录或兄弟 workspace，也不要在仓库里寻找课堂材料。
- 本工程统一使用 Python 3.12 和 pytest；不引入新的第三方依赖。
- 改动放款处理导出（`export_applications` / `POST /api/financing-applications/export`）相关逻辑前，
  先读 `docs/rules/export_eligibility.md`——这是唯一的规则事实源，不要在别处重复整份规则文本。
- 任何改动之后，运行 `./verify.sh`。它会依次跑开发测试（`pytest -q`）和放款导出资格 Golden Case
  （`golden/check_export_eligibility.py`）；两者都通过才算完成，缺一不可。
- `golden/` 下的期望结果来自业务事实，不是开发测试的复制。如果 `./verify.sh` 因为 Golden Case
  失败，先假设业务规则没有变，去检查实现改动；不要为了让它变绿而回头修改 `golden/cases.json`。
- 这条规则的由来：D3 独立验收发现开发方第一次实现和自检都没有见过这条导出资格规则，把不该导出的
  状态一起导出了。修复本身已经在 `app/financing/service.py` 和 `tests/test_export_eligibility.py`
  里；`docs/rules/`、`golden/` 和这份 `./verify.sh` 是为了让下一次开发者或 Agent 不需要重新踩这次
  坑、也不需要重新等一次独立验收才发现这条规则。
- 只做任务需要的最小改动；不要顺手重构、重命名或重新组织你不需要碰的函数和文件——尤其是
  `app/financing/service.py` 里已有的实现结构和变量命名，除非任务本身就是要改它们。
