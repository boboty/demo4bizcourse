# Repository instructions

## Working agreements

- 修改尽量小而聚焦，不顺手重构无关代码。
- 除非任务明确要求，不新增第三方依赖。
- 修改 Python 后运行 `pytest -q`。
- 任务给出验收标准时，把验收标准视为交付契约的一部分。

## Validation discipline

- 开发侧测试只能证明实现与测试彼此一致，不能单独证明业务理解正确。
- 业务规则可由独立验收角色基于单独的 Source of Truth 重新解释与校验。

<!-- Demo 4 才会在这里沉淀具体业务规则。 -->
