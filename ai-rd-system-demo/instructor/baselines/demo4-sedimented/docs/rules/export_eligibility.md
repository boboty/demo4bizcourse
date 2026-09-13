# 放款处理导出资格规则

**Owner：** 融资申请（financing）模块的代码 owner——改动 `app/financing/service.py` 里的导出逻辑（`export_applications`）前，先读这份文件。

**来源：** D3 独立验收（Golden Case GC-02 / GC-03 / GC-04）发现放款处理导出把不允许的状态一起导出了，经独立业务事实源确认后修复。这不是开发方自己发现的问题：开发方第一次实现和开发侧自检当时都没有见过这条规则。

**如何验证：** 运行 `./verify.sh`。它会同时跑开发测试（`pytest -q`）和 `golden/check_export_eligibility.py`——后者是这条规则的独立 policy gate，从业务事实重新计算期望结果，再用真实 HTTP 请求核对系统实际行为，不是开发单元测试的复制。

**什么时候需要修改或废弃这份规则：** 只有业务方就"哪些状态允许进入放款处理导出"给出新的书面决定时才能改；不要因为某次任务改起来更方便就顺手放宽它。改动后必须同步更新 `golden/cases.json` 里的期望值，并说明改动依据。

## 已确认规则

1. **查询资格与放款导出资格是两回事。** 列表查询（`GET /api/financing-applications`）不受导出规则约束，返回内容只看 tenant 权限和筛选条件。
2. **只有 `APPROVED`、`FUNDED` 允许进入放款处理导出**（`POST /api/financing-applications/export`）。
3. **`SUBMITTED`、`REJECTED` 仍然必须可以在列表查询里正常查到，但不得出现在导出结果里。** 即使用户主动把状态筛选设为这两者之一，导出 payload 也必须是空的，不能因为"用户筛选了这个状态"就默认允许导出。
4. **不指定状态筛选（混合结果）导出时，同样只保留 `APPROVED`/`FUNDED`**，其余状态一律不得进入导出 payload。
5. **这条规则不改变既有的 tenant 数据权限范围**（见 `app/common/security.py`）：状态规则不能被用来扩大或绕过 tenant scope，tenant scope 也不能被用来掩盖导出资格问题。两者必须同时成立。
