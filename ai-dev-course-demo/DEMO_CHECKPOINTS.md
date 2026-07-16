# Git 演示检查点

本项目交付五个 annotated tag。附件末尾虽写“四个演示检查点”，前文实际列出五个名称；本项目以五个全部交付为准。

| 检查点 | 用途 | 对应节点 | 应看到的内容 |
| --- | --- | --- | --- |
| `demo-baseline` | Demo 2 开始前的干净代码基线 | 读取项目 | 列表、筛选、Excel helper 和 11 项基础测试；没有导出接口 |
| `demo-initial-implementation` | 首次代码实现完成 | 修改代码 | 导出路由、导出服务、10000 行上限；尚无新增验收测试 |
| `demo-validation-failed` | 真实红灯状态 | 生成测试、首次验证失败 | 新增验收测试，`display_name=None` 导致 `None.strip()`，1 失败、17 通过 |
| `demo-fixed` | 最小修复后的绿灯状态 | 修复并重跑 | null 在导出映射边界变为空字符串，19 项测试通过 |
| `demo-final` | 最终交付 | 变更说明 | 最终代码、全部课堂资产、运行手册和验收报告 |

## 切换命令

只查看某个检查点时使用 detached HEAD，避免移动 `main`：

```bash
git switch --detach demo-baseline
git switch --detach demo-initial-implementation
git switch --detach demo-validation-failed
git switch --detach demo-fixed
git switch --detach demo-final
```

回到最终交付分支：

```bash
./scripts/restore_final.sh
```

该脚本只执行 `git switch main`，不会丢弃或清理本地修改。

## 一键重置

```bash
./scripts/reset_demo.sh
```

脚本使用 `git switch --discard-changes` 切到干净的 `demo-baseline`，丢弃 tracked 演示修改，清理 `app/`、`tests/`、`scripts/` 下的未跟踪实现文件，并保留 `.venv` 和其他位置的讲师笔记。baseline 已包含 Demo 1 任务包和 Demo 2 单次现场输入；最终讲解文档和预跑日志在 `demo-final`/`main` 中。演示结束后运行 `./scripts/restore_final.sh`，即可恢复全部交付资产。

## 失败节点复现

```bash
git switch --detach demo-validation-failed
./scripts/test.sh
```

预期结果是 `test_null_display_name_is_mapped_to_empty_string` 真实失败。不要修改文件制造失败，也不要把失败测试删除后宣称通过。
