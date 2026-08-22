# Round 6A Evidence Map

本文件是课堂证据的唯一映射表。Evidence Level 只使用以下四种：

- `TRUE_DEVICE`：真实物理 iPhone、Safari、Appium/XCUITest 链路产生的结果。
- `CONTROLLED_LOCAL_EXPERIMENT`：本地 Mock 或独立实验真实执行，故障条件由实验明确控制。
- `PREGENERATED_REAL_RESULT`：已经真实执行过、随后脱敏保存的结果；课堂不把它说成现场重新执行。
- `STATIC_ASSET`：代码、YAML、文档或真实生成后保存的静态课堂资产。

| 教学结论 | Evidence Level | 真实来源 | 课堂动作 | 可声称 | 不可声称 |
| --- | --- | --- | --- | --- | --- |
| 自然语言用例还不是机器可执行任务 | `STATIC_ASSET` | `demo0/natural_case.txt`、`demo0/ai_draft_pay_order.yaml`、`demo0/review_notes.md`、`cases/pay_order.yaml`、`docs/executable-task-schema-v1.md` | 依次打开自然语言、AI draft、review notes、最终 YAML | 可执行 task 必须补齐状态、动作、断言、证据和 cleanup | AI 已自动生成生产级自动化框架 |
| 单条支付链路真实跑过物理 iPhone | `TRUE_DEVICE` | Round 1/3 真机运行证据与脱敏摘要；链路为 Mac → Appium → XCUITest/WDA → iPhone → Safari → FastAPI | 运行 V1 baseline，观察 Safari UI 和 API facts | 这条链路真实跑过物理 iPhone | 所有后续实验都是真机执行 |
| Self-Heal 的正式修改由 Gate 控制 | `TRUE_DEVICE` | Round 2 failure bundle、Candidate、Review、3/3 Verify、Write Back、AI-off rerun、restore 证据 | 按 Demo 1 执行 V1 → V2 → failure → candidate → gate → verify → writeback → restore | AI 提出候选，确定性 Review/Verify/Write Back 控制正式资产修改 | AI 可以任意自修复正式回归脚本 |
| Tool → Skill → Workflow 是可验收的工程分层 | `STATIC_ASSET` | `tools/`、`skills/`、`workflows/`、`cases/pay_order.yaml`，并有 Round 3 测试 | 展示调用边界与 `pay_order` / `assert_business_state` 分工 | Tool 做原子动作，Skill 完成语义能力，Workflow 组合业务目标 | 课堂现场重新证明全部抽象或扩展业务范围 |
| Suite/Run Plan 成功记录一次真实失败 | `PREGENERATED_REAL_RESULT` | Round 4 本机真实运行结果与 `evidence/round4-pass-summary.md` | 展示 task → Suite → Run Plan → Report → PRODUCT BUG evidence | Engineering acceptance=PASS；test run=FAIL；total=5、passed=4、failed=1 | 把 Run Plan test result 写成 PASS |
| Retry 是业务语义 | `PREGENERATED_REAL_RESULT` | Round 4 before-commit / after-commit retry history | 展示两条 retry history | 未提交可 Retry 一次；已提交禁止重试 | Retry 是通用技术重试或可以无限重试 |
| Failure Cause 与 Stability 正交 | `CONTROLLED_LOCAL_EXPERIMENT` | `experiments/failure_classification.py`、`experiments/flaky_automation.py`、Round 5 summary | 运行或展示分类与 history summary | Failure Cause 只有 PRODUCT/ENVIRONMENT/DEVICE/AUTOMATION；FLAKY 是 Stability | 把 FLAKY 当成第五种 Failure Cause |
| 四类分类不是四种真机失败 | `CONTROLLED_LOCAL_EXPERIMENT` | PRODUCT 使用本地业务 Mock；AUTOMATION/ENVIRONMENT/DEVICE 使用受控结构化 evidence | 展示四类样本和 UNCLASSIFIED 反例 | 分类依据来自阶段、Skill、facts、device/service evidence | 四种 Failure 都来自真实 iPhone |
| 受控 timing/wait 实验产生 Flaky | `CONTROLLED_LOCAL_EXPERIMENT` | 12 次本地实验、同一 wait timeout、controlled ready delay、真实 `time.monotonic`、JSONL history | 展示 12 条 history 与 summary | 12 runs、6 PASS、6 FAIL、FAIL category=AUTOMATION、stability=FLAKY | 真机自然随机出现 6 次失败 |
| 共享业务状态破坏测试独立性 | `CONTROLLED_LOCAL_EXPERIMENT` | `experiments/shared_state_concurrency.py` 的 barrier、worker timeline、facts | 运行独立 shared-state experiment | 同一 order_id 下一个 committed、一个 already_paid，最终只产生一个 payment | 数据库发生并发写坏或 Suite 已支持 parallel |

## 证据使用规则

课堂展示时必须先说 Evidence Level，再说结论。`artifacts/` 下的原始运行目录、日志、截图和 history 只在本机存在并被 Git ignore；公开材料使用脱敏 summary 或本文件中的静态路径说明。
