# 课堂运行脚本：AI 测试闭环

在项目根目录 `ai-test-loop-demo/` 运行。每一步均为本地确定性执行，无需服务端口、数据库或在线模型。

## Step 0：重置

```bash
python scripts/reset_demo.py
```

## Step 1：查看定义与准备材料

```bash
cat business/requirement.md
cat business/acceptance.md
cat api/openapi.yaml
cat tasks/task-package.md
```

强调：AC-004 要求验证 GOLD 会员判断过程，不能只检查最终金额。

## Step 2：运行 AI 第一次生成的测试

```bash
python scripts/run_generated_tests.py
```

应看到 `ALL TESTS PASSED`。停顿并提问：**测试已经全绿，可以结束了吗？**

## Step 3：运行独立验收

```bash
python scripts/run_independent_review.py
```

应看到：

```text
TEST EXECUTION : PASS
INDEPENDENT REVIEW : REJECTED
Missing:
AC-004 - 关键业务规则缺少有效测试证据
```

独立验收只读取原始需求、验收标准和测试源代码；它没有重新运行 pytest。此处要说明：结果碰巧对，不等于 GOLD 判断过程已被测试证明。

## Step 4：查看遗漏

```bash
cat tests/generated/test_orders.py
cat evidence/independent-review-report.md
```

第一次测试专业地验证了 HTTP、结构、金额守恒、单独的会员/券优惠和不叠加路径，但没有把可叠加的 GOLD + VIP100 场景中的 `membershipDiscount` 与 `CHECK_GOLD_LEVEL` 作为必要断言。

## Step 5：运行修复版

```bash
python scripts/run_verified_tests.py
```

应看到：

```text
pytest: PASS
INDEPENDENT REVIEW : PASS
```

## Step 6：查看沉淀资产

```bash
cat skills/api-test-skill.md
cat evidence/final-test-report.md
```

说明：第一次做对的闭环规则已成为下次可复用的能力模板。

## 课前统一验收

```bash
python scripts/validate_demo.py
```

预期最后一行是 `DEMO STATUS: READY`。

