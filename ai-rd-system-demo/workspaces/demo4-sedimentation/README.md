# Demo 4｜规则沉淀上下文

这是从 Demo 3 正确修复状态开始的独立工程。初始项目规则不包含本次复盘规则；复盘角色先读取 `reports/demo3-validation.md`，再更新 `AGENTS.md` 与 `validation/checklist.md`。随后在同一目录关闭旧会话并新开 Codex。

```bash
pytest -q
```
