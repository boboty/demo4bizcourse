# Demo

AI 研发课程演示合集（monorepo）。每个 demo 一个自包含子目录，自带 `.venv`、`requirements.txt` 与 `scripts/`，可独立安装、运行与测试；所有 demo 共用本仓库的 git 历史。

## Demo 索引

| 目录 | 说明 |
| --- | --- |
| `ai-dev-course-demo/` | 用户列表/筛选/Excel 导出 API 与课堂演示页面（FastAPI） |

## 课堂演示检查点

`ai-dev-course-demo/` 的教学检查点以 annotated tag 形式保存在本仓库：

```bash
git switch --detach demo-baseline   # 查看某个检查点
git switch main                     # 回到最新
```

详见 `ai-dev-course-demo/DEMO_CHECKPOINTS.md`。

## 新增 demo

1. 在根目录新建子目录，按 `ai-dev-course-demo/` 的结构自包含（独立虚拟环境、依赖与脚本）；
2. 直接在本仓库提交，无需为单个 demo 新建仓库。
