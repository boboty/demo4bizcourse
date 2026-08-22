# 调度｜Control plane

目标：完成任务 B，但把“开发完成”和“独立验收”严格分开。

流程：
1. 需求/设计（沉思）读取任务与规则，形成实现建议；
2. Code 角色负责实现与开发侧测试；
3. 验收角色使用独立上下文，按 `validation/independent-validation.md` 执行；
4. 验收出现 BLOCKER 后再回流给 Code 修复；
5. 复盘角色暂不启动，留到 Demo 4。

注意：调度是控制平面，不是第五种业务责任。
