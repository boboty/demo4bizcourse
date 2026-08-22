# Demo

独立可执行代码 Demo 合集（monorepo）。本仓库只维护能够独立安装、运行和测试的代码 Demo；课堂业务规则、任务说明和 Mock 数据等通用课程资产由独立数据仓库维护。

## Demo 索引

| 目录 | 说明 |
| --- | --- |
| `ai-dev-course-demo/` | 用户列表/筛选/Excel 导出 API 与课堂演示页面（FastAPI） |
| `finance-agent-course-demo/` | 离线财务业务智能体课堂演示套件（FastAPI） |
| `ai-test-loop-demo/` | AI 测试闭环：生成测试全绿、独立验收拒绝、修复后沉淀测试能力（FastAPI） |
| `ai-rd-system-demo/` | AI 研发体系课堂 Demo：独立 workspace、黑盒验收与规则沉淀 |

## 课堂演示检查点

`ai-dev-course-demo/` 的教学检查点以 annotated tag 形式保存在本仓库：

```bash
git switch --detach demo-baseline   # 查看某个检查点
git switch main                     # 回到最新
```

详见 `ai-dev-course-demo/DEMO_CHECKPOINTS.md`。

## 新增 demo

1. 在根目录新建子目录，确保 Demo 可独立安装、运行和测试；
2. 直接在本仓库提交，无需为单个 demo 新建仓库。
