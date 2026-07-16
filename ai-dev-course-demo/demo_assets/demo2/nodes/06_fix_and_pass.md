# 节点 6：根据失败修复并重跑通过

> 资产状态：内容来自真实修复提交和真实全量测试摘要；对应截图尚未采集。

## 关键终端日志

```text
$ git show -s --oneline demo-fixed
4e4f92c fix: export null display names as blank

-            clean_text(user.display_name),
+            clean_text(user.display_name or ""),

$ time ./scripts/test.sh
19 passed in 0.36s
real 0.74
```

## 截图建议范围

待采集。画面同时显示针对失败原因的一行修复、补充的接口级 null 单元格测试，以及重跑后的 `19 passed in 0.36s` 和 `real 0.74`。

## 讲师应观察的证据

- 修复只在数据映射边界把 null 转为空字符串，没有扩大到无关模块。
- 除服务层单元测试外，又补充了真实 Excel 回读的接口测试。
- openpyxl 回读空字符串时得到空单元格值 `None`，接口测试据此验证最终文件语义为空。
- 全量测试从 1 失败、17 通过变为 19 项全部通过，且运行时间低于 30 秒。

## 一句讲解提示

修复的可信度来自同一条失败测试转绿并完成全量回归，而不是来自“代码看起来对了”。
