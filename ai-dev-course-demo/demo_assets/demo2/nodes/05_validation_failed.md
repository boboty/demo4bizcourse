# 节点 5：首次验证未通过

> 资产状态：以下为真实预跑保留的失败摘要，不是手工设计的假日志；对应截图尚未采集。

## 关键终端日志

```text
$ time ./scripts/test.sh
AttributeError: 'NoneType' object has no attribute 'strip'
1 failed, 17 passed in 0.36s
real 0.73
```

失败状态对应真实提交：

```text
4f269ee test: add user export acceptance coverage
```

## 截图建议范围

待采集。截图保留完整失败测试名、`AttributeError`、失败/通过计数和命令提示符；建议同时包含指向 `clean_text(user.display_name)` 的调用栈区域。不要只截红色的一行错误。

## 讲师应观察的证据

- 新增验收测试实际发现了 `display_name=None` 时调用 `.strip()` 的边界缺陷。
- 其余 17 项测试通过，失败被定位到单一 null 分支，不应通过删测试或放宽断言处理。
- 失败来自真实测试执行，状态可由 `demo-validation-failed` 检查点复现。
- 执行反馈重新进入修改过程，形成从验证到修复的闭环。

## 一句讲解提示

这就是任务包里验收要素存在的原因。AI写出代码并不代表任务完成，验证结果会重新进入执行过程。
