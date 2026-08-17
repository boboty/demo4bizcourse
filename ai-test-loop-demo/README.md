# AI 测试闭环课堂 Demo

一个完全本地、确定性的 FastAPI + pytest 课堂项目，用于演示：

```text
定义 → 准备 → 执行 ⇄ 验证 → 沉淀
```

它刻意保留两套测试资产：第一次”AI 生成”的测试会全部通过，却遗漏关键业务规则的有效证据；独立验收会拒绝它。修复后的测试同时通过 pytest 和独立验收。

> **关于 `tests/generated/`**：这是为演示构造的失败模式装置，不是某一次真实 AI 生成事件的记录。依据、边界和一次真实的无提示对照实验见 [tests/generated/PROVENANCE.md](tests/generated/PROVENANCE.md)。

## 核心教学点

- AI 会生成测试 ≠ AI 生成了可靠测试；
- 测试通过是证据，不是结论；
- 可验证性决定可委托性；
- HTTP 200、JSON 结构和正确的最终金额，都不能代替对决策过程的业务断言。

## 业务场景

`POST /api/orders/discount-preview` 判断订单优惠资格。GOLD 会员满 1000 元有 100 元会员优惠；`VIP100` 可叠加 100 元券优惠。关键规则为：传入优惠券时不能跳过 GOLD 会员判断。接口用 `membershipDiscount`、`couponDiscount` 和 `decisionTrace` 返回可测试的判断证据。

## 安装与最短课堂命令

Python 3.11+：

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/reset_demo.py
python scripts/run_generated_tests.py
python scripts/run_independent_review.py
python scripts/run_verified_tests.py
```

可选启动接口：

```bash
uvicorn app.main:app --reload
```

访问 `http://127.0.0.1:8000/docs` 查看 API；所有测试本身使用 FastAPI `TestClient`，无需先启动服务。

## 完整验收

```bash
python scripts/validate_demo.py
```

该脚本检查应用/接口 OpenAPI、两套测试、预期的首次拒绝、最终放行、证据文件、reset 幂等性、必需教学资产和无在线服务依赖。

目录中 `business/` 保留原始规则，`tests/generated/` 保留第一次测试，`tests/verified/` 保留修复资产，`evidence/` 保留每次课堂运行生成的证据，`skills/` 是可复用模板。详细讲解顺序见 [docs/classroom-script.md](docs/classroom-script.md)。

