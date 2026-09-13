# Source of Truth｜放款处理导出规则

这份文件是 Demo 3 独立验收时的**业务规则唯一事实源**。开发方在第一次实现和自检时没有见过这份规则。

## 规则

放款处理导出（`POST /api/financing-applications/export`）只允许下列状态的融资申请进入导出结果：

| 状态 | 放款导出 |
|---|---|
| APPROVED | 允许 |
| FUNDED | 允许 |
| SUBMITTED | **禁止** |
| REJECTED | **禁止** |

## 关键提醒

- 这条规则**只约束放款导出**。融资申请列表查询（`GET /api/financing-applications`）不受此规则影响：无论状态是否允许导出，用户都应该能在列表里正常查到 `SUBMITTED` 和 `REJECTED` 的记录。
- "用户筛选了某个状态" 不等于 "这个状态可以导出"。即使用户主动把状态筛选设为 `REJECTED`，导出结果里也不能出现 `REJECTED` 的记录。
- 不指定状态筛选（混合结果）导出时，只保留 `APPROVED` 和 `FUNDED` 的记录，其余状态一律不得进入导出 payload。
- 这条规则不改变既有的 tenant 数据权限范围：某个 tenant 看不到的记录，仍然不能出现在该 tenant 用户的导出结果里；反过来，状态规则也不能被用来扩大或绕过 tenant 权限。
