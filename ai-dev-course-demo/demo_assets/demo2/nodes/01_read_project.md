# 节点 1：读取项目

> 资产状态：节点说明已根据真实预跑提交和当前仓库复核整理；对应截图尚未采集。

## 关键终端日志

真实预跑记录中已确认的摘要：

```text
$ git show -s --oneline demo-baseline
9a5b0ac chore: create course demo baseline

$ ./scripts/test.sh
11 passed in 0.16s
```

## 截图建议范围

待采集。画面同时保留 Codex 已读取的 `AGENTS.md`、`demo_assets/demo2/01_live_prompt.md`，以及对 `app/api/users.py`、`app/services/user_service.py`、`app/utils/excel.py` 的检索或读取记录。终端命令和文件路径必须可见。

## 讲师应观察的证据

- Codex 先读取项目规则，而不是直接写代码。
- Codex 找到现有列表入口和 `UserService.search_users`，确认筛选逻辑的复用点。
- Codex 找到已有的 `build_excel`、`clean_text` 辅助能力和既有测试命令。
- baseline 全量测试为 11 项通过，说明后续结果有可比较的起点。

## 一句讲解提示

先读规则、调用链和测试基线，才能把任务包落到这个项目的真实上下文中。
