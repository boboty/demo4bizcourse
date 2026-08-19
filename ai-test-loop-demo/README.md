# AgentAI 驱动软件测试 — 课堂现场 Demo

一个本地、确定性的 FastAPI 项目，用于课堂现场演示：

> 让另一个 Codex Agent **现场接手一次真实接口测试任务**：
> 读取项目资料 → 理解业务规则 → 自己设计测试 → 执行接口测试 →
> 发现真实 Bug → 给出证据与初步定位。

核心教学点：**接口成功 ≠ 业务正确**。HTTP 200 和 `status=SUCCESS` 只代表请求被正常
处理，不代表计算结果正确；只有对照业务规则验证 `discount` 与 `finalAmount`，才算完成
验收测试。

## 业务场景

`POST /api/orders/calculate` 按会员等级与订单金额计算优惠。

业务规则（唯一 Source of Truth）见 [docs/business-rules.md](docs/business-rules.md)，速览：

- GOLD：`amount >= 1000` → 优惠 200；否则不优惠。
- SILVER：`amount >= 1000` → 优惠 100；否则不优惠。
- STANDARD（普通会员）：一律不优惠。
- 最终应付金额满足 `finalAmount = amount - discount`（例如 GOLD + 1000 → discount=200、finalAmount=800）。

## 启动服务

```bash
source .venv/bin/activate        # 首次使用：python -m venv .venv && pip install -r requirements.txt
uvicorn app.main:app --reload
```

- 接口文档：<http://127.0.0.1:8000/docs>
- 自动 OpenAPI：<http://127.0.0.1:8000/openapi.json>
- 手工调用：

```bash
curl -s http://127.0.0.1:8000/api/orders/calculate \
  -H 'Content-Type: application/json' \
  -d '{"amount": 1000, "memberLevel": "GOLD"}'
```

## 运行项目自带测试

```bash
python -m pytest
```

项目自带测试只是 smoke（接口存在 / HTTP 200 / 返回结构），**不验证任何业务取值**。
根据业务规则验证 `discount` / `finalAmount` 的测试，由课堂现场的 Codex Agent 自己设计生成。

## 课前自检与 Reset

```bash
python scripts/validate_demo.py   # 期望输出 DEMO READY
python scripts/reset_demo.py      # 清空课堂 Agent 工作区，可反复演示
```

- `validate_demo.py`：课前自检——服务可加载、订单接口存在、GOLD+1000 可正常调用、
  文档规定正确值、课堂 Agent 工作区已清空。
- `reset_demo.py`：只清理 `agent_workspace/` 中课堂 Agent 生成的测试、报告与 evidence，
  不修改业务规则与被测代码。

## 课堂工作区

`agent_workspace/` 是课堂现场 Codex Agent 的私有工作区，它在其中生成测试代码、
`test-report.md`、`bug-report.md` 和 `evidence/`。不要提前生成最终答案，让 Agent 现场
完成整个测试闭环。

## 课堂演示流程

1. 课前执行 `python scripts/validate_demo.py`，确认 `DEMO READY`。
2. 启动服务（Agent 也可以直接用 FastAPI `TestClient`，无需端口）。
3. 把任务 Prompt 交给另一个 Codex Agent（模板见 [docs/classroom-script.md](docs/classroom-script.md)）。
4. Agent 自主完成：读资料 → 设计测试 → 执行 → 发现 Bug → 输出证据与定位。
5. 讲师对照 `docs/business-rules.md` 复盘 Agent 的 `bug-report.md`。
6. 课后执行 `python scripts/reset_demo.py`，可反复演示。

环境搭建细节见 [SETUP.md](SETUP.md)；旧版 Demo 材料已归档到 `archive/old-demo/`，不属于本课。
