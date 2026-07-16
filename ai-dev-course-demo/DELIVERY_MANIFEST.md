# 交付文件清单

## 可运行项目

- `app/`：FastAPI 路由、模型、仓储、列表服务、导出服务和 Excel helper。
- `tests/`：基础列表、仓储、Excel、导出边界、接口和教学资产一致性测试。
- `requirements.txt`、`pyproject.toml`：Python 3.11+ 依赖和 pytest 配置。
- `scripts/setup.sh`、`run.sh`、`test.sh`、`reset_demo.sh`、`restore_final.sh`：幂等安装、启动、测试、一键重置和安全切回 `main`。
- `AGENTS.md`：Codex 执行时使用的项目规则。

## Demo 1

- `demo_assets/demo1/01_ambiguous_request.md`
- `demo_assets/demo1/02_direct_prompt.md`
- `demo_assets/demo1/03_task_package.md`
- `demo_assets/demo1/04_comparison.md`
- `demo_assets/demo1/05_minimum_task_package.md`
- `demo_assets/demo1/06_practice_card.md`
- `demo_assets/demo1/outputs/direct_run.md`
- `demo_assets/demo1/outputs/task_package_run.md`

## Demo 2

- `demo_assets/demo2/01_live_prompt.md`：与 Demo 1 完整任务包逐字一致。
- `demo_assets/demo2/nodes/`：七节点说明。
- `demo_assets/demo2/logs/`：真实 baseline、失败和修复通过日志。
- `demo_assets/demo2/recording/`：尚未实际录制的录屏采集计划与讲师脚本。
- `demo_assets/demo2/screenshots/SCREENSHOT_CHECKLIST.md`：尚未实际采集的七截图清单。

## 运行与验收

- `DEMO_CHECKPOINTS.md`：五个 Git 检查点的用途和切换方法。
- `DEMO_RUNBOOK.md`：现场步骤、三个暂停点和第 20 分钟时间闸门。
- `CHANGE_SUMMARY.md`：变更范围、验证证据和限制。
- `ACCEPTANCE_REPORT.md`：逐项验收结果。

## 未生成的二进制资产

- `demo2_full_run.mp4`：未录制。
- `01_read_project.png` 至 `07_change_summary.png`：未采集。

以上未生成项已明确保留为环境限制，不使用占位文件或伪造界面替代。
