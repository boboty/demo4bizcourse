# Demo 资产验收清单

## 总体
- [ ] 四次都真正退出 PPT；Demo 1A 使用 CNN 可视化，1B/2/3/4 进入真实电脑操作。
- [ ] 同一个仓库，两条任务线；没有第四个业务细节。
- [ ] 每个 Demo 都能用一句承重判断收口。
- [ ] 所有操作有 reset / deterministic fallback。

## Demo 1
- [ ] CNN 页面提前打开并验证可用。
- [ ] 准备 2–3 个容易产生歧义的数字写法。
- [ ] Codex 一句话任务无论“直接做 / 追问 / 做对”都能收口。

## Demo 2
- [ ] 五要素文字与课件 P37–41 一致。
- [ ] `python instructor/checks/task_a_acceptance.py` 能验单条件、多条件、空结果、权限、异步导出、前端控件。
- [ ] 学员实战 25 分钟：5+12+5+3。

## Demo 3
- [ ] `pytest -q tests/test_settlement_developer.py` 在 wrong state 全绿。
- [ ] `python validation/independent_check.py` 在 wrong state 必须 BLOCKER。
- [ ] GC-01 的差异必须是 6200 combined vs 5000 refund-only。
- [ ] 验收角色在形成期望前看不到实现、开发测试和开发聊天。
- [ ] fixed state 下开发测试 + independent check 全绿。

## Demo 4
- [ ] 复盘新增的是规则与检查项，不是这次案例金额。
- [ ] 必须新开 Codex 会话验证规则加载。
- [ ] 新会话变体结果：FX_LOSS_PLUS_TAX_REFUND / 11000。
