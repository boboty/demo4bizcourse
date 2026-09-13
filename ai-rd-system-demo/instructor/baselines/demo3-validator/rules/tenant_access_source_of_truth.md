# Source of Truth｜tenant 数据权限

这是独立验收时使用的用户 tenant 权限对照表，来自业务侧的用户权限台账，与开发实现无关。

| 用户 | 可见 tenant |
|---|---|
| alice | NORTH |
| bob | SOUTH |
| admin | NORTH, SOUTH |

任何一次查询或导出，返回记录的 tenant 都必须落在该用户的可见 tenant 范围内；状态相关的导出规则（见 `export_eligibility_source_of_truth.md`）不能扩大或缩小这个范围。
