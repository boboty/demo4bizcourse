# 双 Demo 运行手册

## 0. 课前预检

在项目根目录执行：

```bash
./scripts/setup.sh
./scripts/test.sh
./scripts/reset_demo.sh
```

确认 Python 为 3.11+、最终全量测试通过、`demo-baseline` 可切换。`setup.sh` 可重复执行：已有有效的 Python 3.11+ `.venv` 时复用并安装依赖，缺失或不兼容时才安全重建；安装优先使用 `uv`，没有 `uv` 时使用本机 Python 3.11+ 和标准 `venv`。应用运行时不访问外部 API、数据库或云服务；首次安装依赖可能需要包索引网络。

`reset_demo.sh` 会丢弃 tracked 代码修改并清理 `app/`、`tests/`、`scripts/` 下的未跟踪实现文件；课前先保存需要保留的代码或补丁。其他目录下的讲师笔记不会被该脚本清理。

## 1. Demo 1：从模糊需求到可验证任务

1. 展示 `demo_assets/demo1/01_ambiguous_request.md`。
2. 展示 `02_direct_prompt.md`，再用 `outputs/direct_run.md` 的真实隔离预跑说明 AI 自行补充了哪些假设、遗漏了哪些边界。
3. 打开 `03_task_package.md`，按背景、目标、输入、约束、输出、验收六部分讲解。
4. 用 `04_comparison.md` 对比是否可验收，而不是对比字数。
5. 用 `05_minimum_task_package.md` 说明日常任务可只保留目标、约束、验收。
6. 发放 `06_practice_card.md` 做纸面跟练。

核心结论：AI研发的第一步不是让AI开始写代码，而是把工作定义成边界清晰、结果可验证的任务。

## 2. Demo 2：运行完整研发闭环

1. 确认代码处于 `demo-baseline`，打开 `demo_assets/demo2/01_live_prompt.md`。
2. 将该文件全文一次性提交给 Codex；后续原则上不再逐步告诉 Codex 下一步做什么。
3. 按 `demo_assets/demo2/nodes/` 的顺序观察七个节点：读取项目、制定计划、修改代码、生成测试、首次验证失败、修复重跑、变更说明。
4. 在计划、首次验证失败、变更说明三个节点暂停；讲解提示已写入对应节点文件。
5. 现场执行直接通过时，不要求为了演出效果制造失败；改用 `demo-validation-failed` 的真实预跑记录说明失败闭环。

核心结论：AI写出代码不是闭环；AI能够读取工程反馈、发现问题并修正，才形成研发执行闭环。

## 3. 第 20 分钟时间闸门

Demo 2 第20分钟仍未进入测试环节，停止等待现场执行；切换到同一项目、同一任务的真实预跑记录。不重新输入需求，不临时人工补写代码。

切换话术：

> 当前执行已经超过课堂时间闸门。智能体真实运行存在时长不确定性，我们切换到同一任务的完整预跑记录，继续看验证、修复和交付闭环。

切换顺序：

```bash
git switch --detach demo-validation-failed
./scripts/test.sh
git switch --detach demo-fixed
./scripts/test.sh
git switch --detach demo-final
```

## 4. 现场运行 API

```bash
./scripts/run.sh
```

另一个终端可访问 `http://127.0.0.1:8000/docs`，或直接请求：

```text
GET http://127.0.0.1:8000/api/users?status=active
GET http://127.0.0.1:8000/api/users/export?status=active
```

## 5. 兜底资产状态

- 一级录屏：当前环境未采集；录制要求与流程见 `demo_assets/demo2/recording/`。
- 二级截图：当前环境未采集；七张图的范围与文件名见 `demo_assets/demo2/screenshots/SCREENSHOT_CHECKLIST.md`。
- 三级 Git 检查点：五个 tag 已按真实提交链路建立，可现场切换。

不得把录屏计划、截图清单或整理摘要描述成已经采集的真实素材。

## 6. 故障排查速查

| 现象 | 处理方式 |
| --- | --- |
| 提示缺少 `.venv` 或依赖 | 重复执行 `./scripts/setup.sh`；有效环境会被复用，不会因目录已存在而失败 |
| 提示需要 Python 3.11+ | 安装 Python 3.11+ 或 `uv`，然后重新执行 `./scripts/setup.sh` |
| 首次依赖安装失败 | 检查包索引网络后重试 `./scripts/setup.sh`；应用和测试运行阶段不需要外网 |
| 8000 端口已占用 | 关闭旧进程，或执行 `PORT=8001 ./scripts/run.sh` 改用其他端口 |
| 检查点测试结果不符合预期 | 先用 `git status` 确认没有现场改动，再按 `DEMO_CHECKPOINTS.md` 切换对应 tag |
| 需要回到最终交付 | 执行 `./scripts/restore_final.sh`，安全切回 `main` |
