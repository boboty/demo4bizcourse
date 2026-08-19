# 课堂现场脚本：AgentAI 驱动软件测试

目标：让另一个 Codex Agent 现场接手一次真实接口测试任务，独立完成
「读资料 → 理解规则 → 设计测试 → 执行 → 发现 Bug → 证据与定位」。

## 课前（讲师）

```bash
python scripts/validate_demo.py    # 期望最后一行 DEMO READY
python scripts/reset_demo.py       # 确保 agent_workspace/ 为空
```

## 课堂开场（讲师）

1. 说明任务：`/api/orders/calculate` 是刚上线的订单优惠计算接口，需要按业务规则验收。
2. 强调：HTTP 200 / `status=SUCCESS` 不等于业务正确，必须核对 `discount` 与 `finalAmount`。
3. 把任务 Prompt 交给另一个 Codex Agent，指定工作区为 `agent_workspace/`。

## 现场 Agent 流程（另一个 Codex）

1. 读取 `docs/business-rules.md`（业务 Source of Truth）；
2. 查看 FastAPI 自动 OpenAPI（`/openapi.json`）或 `api/openapi.yaml`（请求/返回字段）；
3. 读取 `README.md`（启动与测试方式）；
4. 自行设计测试矩阵（正常、边界、非法输入）；
5. 执行接口测试并记录真实响应；
6. 对照业务规则核对 `discount` / `finalAmount`；
7. 在 `agent_workspace/` 输出测试代码、`test-report.md`、`bug-report.md`、`evidence/`。

## 复盘（讲师）

- 对比 Agent 的 `bug-report.md` 与 `docs/business-rules.md`；
- 关键提问：接口返回 200、`status=SUCCESS`，业务就对了吗？
- 检查 Agent 是否验证了 `finalAmount = amount - discount`，而不是只看 HTTP 层。

## 课后（讲师）

```bash
python scripts/reset_demo.py
```

## 建议任务 Prompt

```text
你是测试工程师。请现场完成订单优惠计算接口的验收测试，并交付可审计的证据。

项目：ai-test-loop-demo（当前工作目录）
工作区：agent_workspace/（所有产物都放这里）
业务依据：docs/business-rules.md（唯一 Source of Truth）
接口定义：FastAPI 自动 OpenAPI（启动后 /openapi.json）与 api/openapi.yaml
启动方式：见 README.md（也可用 FastAPI TestClient，无需起服务）

边界：scripts/ 下的脚本是讲师工具，不属于被测资料，不要读取其中的判定结论；
请完全依据业务规则和接口真实响应得出结论。

请完成：
1. 阅读业务规则，整理正常 / 边界 / 异常测试点；
2. 自行设计并执行接口测试；
3. 用真实响应核对 discount 与 finalAmount 是否符合业务规则；
4. 若接口行为与业务规则不符，输出证据（原始请求/响应）与初步定位（接口、字段、规则）；
5. 在 agent_workspace/ 交付：测试代码、test-report.md、bug-report.md、evidence/。

注意：HTTP 200 和 status=SUCCESS 不代表业务正确，务必逐条核对业务规则。
```
