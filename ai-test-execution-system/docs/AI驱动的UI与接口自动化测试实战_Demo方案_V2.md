# 《AI驱动的UI与接口自动化测试实战》Demo 方案 V2

> 用途：课程 Demo 工程实施基线。  
> V2 吸收上一轮审核意见后重排范围、轮次与验收门禁。  
> 原则：**Demo 是课程观点的证据，不是课程主线。工程实际产出什么，课件最终就引用什么。**

---

# 一、总体目标

本课程不做多个彼此独立的小 Demo，而是围绕**同一套可运行工程**逐步增加复杂度。

统一业务链：

> **登录 → 下单 → 付款 → 查询**

整套 Demo 最终需要证明六件事：

1. 自然语言测试用例不能直接等同于机器可执行任务；
2. AI 可以帮助把自然语言用例整理成结构化任务，但缺失约束必须显式补齐；
3. UI 自动化可以真实连接 iPhone 真机执行，而且真机会引入模拟器/无头浏览器没有的设备状态问题；
4. API 可以负责测试数据准备、最终业务事实验证与清理；
5. 单个用例可以扩展为 Suite、运行计划、证据保存与运行报告；
6. AI 可以参与异常诊断和自愈，但修复结果必须经过验证并沉淀为确定性资产。

课程最终结论：

> **AI 可以处理不确定性，但测试结果的判定依据必须确定。**

---

# 二、工程定位

Demo 工程放在现有课程 Demo 项目下，作为独立子项目：

```text
Demo/
└── ai-test-execution-system/
```

它是一套**课堂参考实现**，不是商业级测试平台。

设计目标优先级：

1. 课堂稳定；
2. 过程可解释；
3. 每个关键结论都有真实工程证据；
4. 所有演示可 reset；
5. 讲师可以脱离 Codex 独立完成演示；
6. 工程文件、课件截图/配置、课堂口播三者一致；
7. 最后才考虑扩展性。

明确不追求：

- 完整测试平台 UI；
- 通用并行执行器；
- 真正的 Cron 常驻调度服务；
- 多设备池管理；
- 独立报表平台；
- 商业级设备云；
- 通用 AI 测试产品；
- 为了对齐课件而人为凑固定用例数量。

总原则：

> **这是课堂证据系统，不是商业测试平台。**

---

# 三、三场课堂演示

整天只安排三次真正需要切出课件、进入工程环境的演示。

---

## Demo 0：从自然语言用例到可执行任务

### 时长

5–8 分钟。

### 对应课程内容

第一部分：

> 需求 → 测试点 → 用例 → 可执行任务

### 演示目的

**不是再演一次“AI 会生成测试用例”。**

重点是证明：

> **人能读懂的测试用例，与机器可以稳定执行的任务，中间还差一层工程约束。**

### 输入

准备一条已经存在的自然语言测试用例：

```text
前置：用户存在一笔待付款订单。

步骤：
1. 登录系统；
2. 进入待付款订单；
3. 点击立即支付；
4. 验证支付成功。
```

### 第一次让 AI 转换

要求 AI：

> 把这条测试用例转换成机器可执行的 YAML 任务。

AI 很可能生成一个“看上去完整”的结果。

### 现场不直接接受

讲师当场检查：

- `device_id` 从哪里来？
- 测试账号是谁？
- 订单如何准备？
- `order_id` 如何获得？
- 支付成功到底以什么为准？
- 只有 UI 文案还是还要验证 API / 数据？
- timeout 怎么处理？
- 失败时留什么证据？
- 执行完如何 cleanup？
- 哪些变量需要参数化？

### 第二次补齐

给 AI 提供已知确定性约束，再生成结构化任务。

最终得到真实工程中的：

```text
cases/pay_order.yaml
```

### 课堂落点

> **AI 能帮你把信息结构化，但它不知道的事实，不能靠它猜。**

以及：

> **测试用例 ≠ 可执行测试任务。**

---

# 四、统一技术方案

## 4.1 被测业务系统

采用：

> **FastAPI + 简单移动端 Web UI**

业务系统完全由课程工程控制，不依赖外部网站，不接真实支付。

最小业务模型：

```text
User
Product
Order
Payment
Inventory
```

订单状态：

```text
CREATED
  ↓
PENDING_PAY
  ↓
PAID
```

付款必须产生独立 `Payment` 记录。

库存单独存在，是为了能够注入一个真正的 Product Bug：

```text
付款成功
订单变 PAID
但库存没有扣减
```

### 支付接口必须提供可控故障模式

例如：

```text
normal
timeout_after_commit
timeout_before_commit
```

目的：支持下午的 Retry 业务语义演示。

### 必须提供支付事实查询接口

至少可以查询：

```text
order.status
payment_count
payment_status
inventory
```

---

## 4.2 Web UI 一开始就做两版

不要到 Self-Heal 阶段再回头改页面。

### UI V1

例如支付按钮：

```html
<button id="pay-now">立即支付</button>
```

### UI V2

例如改为：

```html
<button data-testid="confirm-payment">确认支付</button>
```

或者调整 DOM 层级，但保持业务语义不变。

必须支持通过配置切换：

```text
UI_VERSION=v1
UI_VERSION=v2
```

这样 Self-Heal Demo 可以稳定复现：

```text
V1 → deterministic PASS
V2 → old locator 必然 FAIL
```

---

## 4.3 真机执行

首选：

> **iPhone 真机 + USB + Xcode / WebDriverAgent + Mobile Safari + Appium XCUITest Driver**

Mac 侧运行：

```text
FastAPI
Appium Server
Test Runner
AI Analyzer
QuickTime Player
会议软件
```

iPhone 真机负责：

```text
Mobile Safari UI
系统级设备状态
```

优先 USB 连接；课前完成设备信任、Developer Mode 与 WebDriverAgent 的 Personal Team 重新签名。

---

# 五、真机必须有“非真机不可”的证据

纯网页操作不足以证明为什么要用真机。

因此上午主 Demo 必须加入一个**可控的设备级干扰**。

首选：

> **Safari 页面主动请求定位权限 → iOS 显示系统权限弹窗 → 设备级自动化处理 → 继续执行**

原因：

- 可由课堂页面主动触发；
- 可控；
- 不依赖随机通知；
- 真正属于系统层，且不属于普通 Web DOM；
- 可以自然回收“AVAILABLE / PREPARING / RUNNING / RECOVERING / RESETTING”。

备选方案：

- 原生系统权限弹窗；
- Safari 权限弹窗；
- 输入法遮挡；
- App/Safari 被系统切后台。

但只选一个作为主演示，避免增加现场变量。

---

# 六、UI / API 分工

整套 Demo 固定采用：

> **API 准备世界 → UI 验证用户旅程 → API 确认业务事实**

例如付款：

```text
API：
创建/获取测试账号
创建商品
准备待付款订单
        ↓
UI：
登录
打开订单
点击付款
看到支付成功
        ↓
API：
order.status == PAID
payment_count == 1
inventory 已正确变化
        ↓
Cleanup：
重置订单 / 支付 / 库存 / 测试账号状态
```

课堂落点：

> 不要为了测试 UI，把所有事情都放在 UI 上完成。

---

# 七、建议工程目录

V2 进一步削减不必要的平台化组件。

```text
ai-test-execution-system/
│
├── README.md
├── AGENTS.md
├── pyproject.toml
├── .env.example
│
├── app/
│   ├── api/
│   ├── web/
│   └── data/
│
├── cases/
│   ├── pay_order.yaml
│   └── ...
│
├── suites/
│   └── nightly.yaml
│
├── schedules/
│   └── nightly.yaml
│
├── ui/
│   ├── driver.py
│   ├── locators/
│   └── actions/
│
├── api/
│   ├── client.py
│   └── assertions.py
│
├── devices/
│   ├── state.py
│   ├── healthcheck.py
│   └── reset.py
│
├── skills/
│   ├── prepare_pending_order/
│   ├── login/
│   ├── open_pending_order/
│   ├── pay_order/
│   ├── assert_business_state/
│   ├── reset_order/
│   ├── classify_failure/
│   └── generate_run_report/
│
├── self_heal/
│   ├── analyzer.py
│   ├── candidate.py
│   ├── verifier.py
│   └── writeback.py
│
├── runner/
│   ├── case_runner.py
│   ├── suite_runner.py
│   └── run_plan.py
│
├── artifacts/
│   └── runs/
│
├── reports/
│
├── experiments/
│   └── shared_state_concurrency.py
│
├── instructor/
│   ├── demo-runbook.md
│   ├── acceptance-checklist.md
│   └── expected-observations.md
│
└── scripts/
    ├── start_demo.sh
    ├── reset_demo.sh
    ├── check_environment.sh
    └── restore_self_heal_baseline.sh
```

说明：

- 不做通用设备池；
- 不做 Cron daemon；
- 不做复杂 scheduler；
- 不做报表平台；
- `schedules/nightly.yaml` 是运行计划配置；
- `--run-now` 负责课堂触发；
- 并发只作为 `experiments/` 下的课堂实验，不成为框架正式能力。

---

# 八、Demo 1：上午主 Demo

## 主题

> **一条支付任务，怎样在真机上可信地跑完**

### 建议时长

20–25 分钟。

---

## 8.1 第一段：确定性执行

从真实文件开始：

```text
cases/pay_order.yaml
```

具体 Schema 由工程实现确定，课件最终反向同步。

执行：

```text
API prepare
   ↓
order = PENDING_PAY
   ↓
iPhone Mobile Safari
   ↓
Login
   ↓
Open order
   ↓
Pay
   ↓
UI payment_success
   ↓
API verify
   ↓
order.status = PAID
payment_count = 1
inventory 正确
```

同时生成：

```text
artifacts/runs/<run-id>/
├── result.json
├── timeline.json
├── screenshots/
├── ui.log
├── api.log
├── device.log
└── retry_history.json
```

---

## 8.2 第二段：插入设备级干扰

执行中主动锁屏。

期望看到：

```text
RUNNING
   ↓
device unavailable
   ↓
RECOVERING
   ↓
wake / unlock / restore
   ↓
RUNNING
```

如果恢复失败：

```text
BROKEN
```

课堂落点：

> **UI 自动化真正难维护的不只是页面元素，更是一个可重复的设备状态。**

---

## 8.3 第三段：切换 UI V2

切换：

```text
UI_VERSION=v2
```

旧确定性资产必须失败：

```text
DETERMINISTIC EXECUTION
        ↓
       FAIL
```

不允许测试框架静默兜底。

---

## 8.4 第四段：AI 产生 Repair Candidate

AI Analyzer 只需要四类输入：

```text
失败步骤
失败截图
当前页面源码 / DOM
目标语义
```

可以附带旧 locator，但不需要堆过多上下文。

AI 输出：

```yaml
target: pay_button

old:
  strategy: id
  value: pay-now

candidate:
  strategy: testid
  value: confirm-payment

evidence:
  unique_match: true
  semantic_text: "确认支付"
```

### 明确删除

不输出：

```text
confidence: 0.91
```

原因：

> 模型自报置信度不是可校准概率，也不是测试判定依据。

---

## 8.5 第五段：Review / Verify / Write Back

治理顺序采用：

```text
Repair Candidate
      ↓
Review / Policy Gate
      ↓
Verifier
      ↓
固定断言通过
      ↓
重复执行稳定
      ↓
Write Back
```

### Review 检查

- 修改范围是否只触及 locator / 允许资产？
- 是否改变了原始业务目标？
- 是否绕过了关键操作？
- 是否扩大了 AI 自由度？

### Verify 检查

- 新 locator 在页面是否唯一？
- UI 关键步骤是否重放成功？
- API 固定断言是否仍然满足？
- 连续重放是否稳定？

然后正式写回。

随后完整执行第二次：

```text
DETERMINISTIC EXECUTION
        ↓
       PASS
```

### Demo 高潮

> **第一次证明 AI 聪明；第二次证明系统变厚了。**

---

# 九、Self-Heal Reset

必须支持：

```bash
./scripts/restore_self_heal_baseline.sh
```

它至少恢复：

```text
旧 locator
UI 版本状态
repair candidate 目录
writeback 结果
测试数据
```

确保：

> 每次彩排、每次开课，Self-Heal Demo 都能重新从“必然失败”开始。

`reset_demo.sh` 必须包含这一动作，或者明确调用它。

---

# 十、Demo 2：下午主 Demo

## 主题

> **从一个用例，到一批可追溯的回归结果**

### 建议时长

约 20 分钟。

### 目标

证明：

```text
Case
→ Suite
→ Run Plan
→ Artifacts
→ Classification
→ Report
→ History
```

不追求“大平台”。

---

# 十一、Suite

真实文件：

```text
suites/nightly.yaml
```

正式 Suite V1 只保证：

> **串行执行**

因为本课重点不是建设并发调度器。

Suite 配置需要表达：

- cases；
- data scope；
- reset policy；
- stop / continue 策略；
- shared-state rule；
- device requirement。

具体 Schema 由 Round 4 后冻结。

---

# 十二、共享状态并发实验

为了真实证明：

> **并发会放大共享状态污染。**

单独提供一个课堂实验：

```text
experiments/shared_state_concurrency.py
```

或两个独立 Case Runner 同时启动。

故意让两个 Case 共用：

```text
同一 order
或同一 inventory
```

结果应出现：

```text
随机红
状态冲突
后执行者看到的世界已经被前一个改变
```

这个实验不进入正式 Suite 能力。

课堂落点：

> **不是所有能并发的代码，都应该并发执行。**

---

# 十三、Run Plan / Schedule

保留真实文件：

```text
schedules/nightly.yaml
```

但不实现真正 Cron daemon。

表达：

```text
trigger
environment
preflight
suite
artifact retention
on_finish
notify（可选，仅配置）
```

课堂使用：

```bash
python -m runner.run_plan --run-now schedules/nightly.yaml
```

重点是：

> 多用例定时执行首先是一份可审查的运行计划，不是“写个 cron 就结束”。

---

# 十四、Retry 必须进入正式工程

支付接口提供：

```text
timeout_before_commit
timeout_after_commit
```

## Case A：timeout_before_commit

```text
请求 timeout
↓
查询支付事实
↓
NOT PAID
↓
允许 retry
```

## Case B：timeout_after_commit

```text
支付已成功
响应 timeout
↓
查询支付事实
↓
PAID
↓
禁止再次支付
```

必须保存：

```text
retry_history.json
```

课堂落点：

> **Retry 不是技术策略，而是业务语义。**

---

# 十五、故障分类

最终至少覆盖四类：

```text
PRODUCT
ENVIRONMENT
DEVICE
AUTOMATION
```

`FLAKY` 不作为与上述完全同级的“原因”，而作为：

> **跨 Run 的稳定性标签**

例如：

```text
category: AUTOMATION
stability: FLAKY
```

---

## 15.1 Product

例如：

```text
支付成功
订单 PAID
库存未扣减
```

---

## 15.2 Device

例如：

```text
设备掉线
无法唤醒
Appium session 断开
```

---

## 15.3 Automation

例如：

```text
locator 错误
wait timeout
自动化脚本问题
```

---

## 15.4 Environment

例如：

```text
测试服务不可用
依赖服务异常
测试数据准备失败
```

---

# 十六、Flaky 历史

不能靠单次 Nightly Run 证明 Flaky。

因此增加轻量历史：

```text
artifacts/history/<case-id>.jsonl
```

连续运行同一个 Case 10–12 次。

例如：

```text
PASS
PASS
FAIL
PASS
PASS
FAIL
PASS
...
```

生成简单历史视图：

```text
Case: pay_order
Runs: 12
PASS: 10
FAIL: 2
Stability: FLAKY
```

不做 Dashboard。

课堂落点：

> **Flaky 不是失败多，而是同一个用例在可比条件下结果会漂。**

真正被消耗的是：

> **团队对自动化结果的信任。**

---

# 十七、Run Report

最终真实生成：

```text
reports/<run-id>.md
```

或简单 HTML。

不要求独立报表系统。

报告至少包含：

```text
Total
PASS
FAIL
SKIP

Product failures
Environment failures
Device failures
Automation failures
Flaky cases
Duration
```

每个失败可追溯：

```text
Screenshot
Page Source / UI Evidence
Device Log
API Trace
Timeline
Retry History
Failure Classification
```

### 数字原则

不预设：

```text
20 Total / 17 PASS / 3 FAIL
```

最终真实跑出什么，就使用什么。

例如真实结果是：

```text
12 Total
9 PASS
3 FAIL
```

课件就改成 `12 / 9 / 3`。

原则：

> **真实比漂亮重要。**

---

# 十八、Tool / Skill / Workflow

工程目录作为唯一权威。

---

## 18.1 Tool

原子能力，例如：

```text
tap
input
swipe
http_request
ios_device_health_check
```

---

## 18.2 Skill

带业务语义、前置、断言和失败返回：

```text
prepare_pending_order
login
open_pending_order
pay_order
assert_business_state
reset_order
classify_failure
generate_run_report
```

---

## 18.3 Workflow

例如：

```text
pay_order_and_verify
```

组合：

```text
prepare_pending_order
   ↓
login
   ↓
open_pending_order
   ↓
pay_order
   ↓
assert_business_state
   ↓
reset_order
```

第五部分不单独再造聊天框 Demo。

---

# 十九、Agent 收口

直接展示真实执行 Trace：

```text
Agent receives task
        ↓
prepare_pending_order
        ↓
login
        ↓
open_pending_order
        ↓
pay_order
        ↓
assert_business_state
        ↓
classify_failure（异常时）
        ↓
generate_run_report
```

口播转场：

> 前面解决的是“我们已经有哪些能力”。

然后问：

> **谁根据任务、环境和当前状态，把这些能力组织起来？**

Agent 在这里出现。

---

# 二十、设备状态模型

统一状态：

```text
AVAILABLE
    ↓
PREPARING
    ↓
RUNNING
    ↓
RECOVERING / RESETTING
    ↓
AVAILABLE
```

异常出口：

```text
BROKEN
```

Baseline 不是状态。

它是回到 `AVAILABLE` 前必须满足的一组检查：

```text
iPhone USB 已连接且受信任
Mobile Safari 可用
Appium 可建立 session
iPhone 已解锁且 Developer Mode 已启用
WebDriverAgent 已由 Personal Team 签名并可启动
无残留系统弹窗
网络可用
测试账号状态正确
业务数据已 reset
```

---

# 二十一、实施轮次

V2 重新排序为：

```text
Round 0
环境 + 真机 + 投屏门禁
        ↓
Round 0.5
被测业务系统 + UI V1/V2 + 故障开关
        ↓
Round 1
Demo 0 + 单案例确定性闭环
        ↓
Round 2
Route C Self-Heal + 资产回滚
        ↓
Round 3
UI/API + Tool/Skill/Workflow 整理
        ↓
Round 4
Suite + Run Plan + Retry + Report
        ↓
Round 5
故障分类 + 并发污染实验 + Flaky 历史
        ↓
Round 6
工程 / 课件 / Runbook 对齐
```

---

# 二十二、Round 0：环境与投屏门禁

这一轮不写业务功能。

检查：

```text
Python
Node
Appium
Xcode
XCUITest Driver
WebDriverAgent
iPhone USB 连接
Developer Mode
Mobile Safari
QuickTime Player
实际会议软件共享
```

最小验证：

```text
Mac 启动静态页面
        ↓
iPhone Mobile Safari 打开
        ↓
Appium + XCUITest 建立真机 session 并找到按钮
        ↓
点击
        ↓
页面产生可验证变化
        ↓
保存截图
        ↓
QuickTime 通过 USB 在 Mac 清晰显示 iPhone 画面
        ↓
会议软件共享后仍然可看清
```

### 必须用实际上课会议平台彩排

需要确认：

- 竖屏 iPhone 大小；
- QuickTime 窗口大小；
- 共享区域；
- 字体可读性；
- 网络端观看延迟；
- 是否需要横屏。

### 门禁

Round 0 不通过：

> **停止整个项目。**

不接受：

> “代码已经准备好，只是当前没有真机验证。”

---

# 二十三、Round 0.5：被测业务系统

完成：

```text
FastAPI
User
Product
Order
Payment
Inventory
Mobile Web UI
UI V1
UI V2
```

并一次性加入可控开关：

```text
UI_VERSION
PAYMENT_MODE
PRODUCT_BUG_MODE
DEVICE_DEMO_MODE（如需要）
```

### 门禁

1. API 可以准备 `PENDING_PAY`；
2. Web 可以完成登录 / 打开订单 / 付款 / 查询；
3. 付款会产生独立 Payment；
4. 能查询支付最终事实；
5. V1/V2 可切换；
6. Product Bug 可以打开/关闭；
7. timeout_before_commit 可复现；
8. timeout_after_commit 可复现；
9. 所有关键 UI 元素有稳定测试属性；
10. reset 后回到确定基线。

---

# 二十四、Round 1：Demo 0 + 单案例闭环

## Part A：Demo 0

完成：

```text
natural_case.txt
→ LLM transform
→ draft task
→ constraint review
→ cases/pay_order.yaml
```

必须保存：

```text
input
AI draft
review notes
final task
```

## Part B：确定性执行

完成：

```text
API prepare
→ 真机 UI
→ 支付
→ API verify
→ evidence
→ cleanup
```

### 门禁

1. `pay_order.yaml` 是真实入口；
2. 不写死 `order_id`；
3. API 真正准备 PENDING_PAY；
4. UI 真正在 iPhone 真机；
5. PASS 不只看 UI；
6. API 至少验证：
   - order.status == PAID
   - payment_count == 1
7. 失败有截图；
8. 设备日志可追溯；
9. cleanup 有效；
10. 连续跑 5 次结果一致。

---

# 二十五、Round 2：Route C Self-Heal

增加：

```text
locator failure
AI analyzer
repair candidate
review
verifier
writeback
rollback
```

### 门禁

必须证明：

```text
UI V2
↓
旧资产 deterministic FAIL
↓
AI candidate
↓
Review
↓
Verify
↓
Write Back
↓
第二次 deterministic PASS
```

并且：

- AI 不直接改正式资产；
- 不允许修改业务断言；
- 不允许修改被测 `app/` 让测试通过；
- reset 后可以重新制造 FAIL；
- 连续彩排至少 3 次完整链路。

---

# 二十六、Round 3：Skill 化与分层

把已经跑通的能力整理成：

```text
Tool
Skill
Workflow
```

并冻结第一版任务 Schema。

这时才确定：

```text
cases/pay_order.yaml
skills/*
```

的最终真实结构。

### 门禁

- Tool / Skill / Workflow 无命名冲突；
- Skill 有明确输入输出；
- Skill 有前置条件；
- Skill 有断言；
- Skill 有失败返回；
- Workflow 不隐藏固定断言。

---

# 二十七、Round 4：Suite + Run Plan + Retry + Report

完成：

```text
suites/nightly.yaml
schedules/nightly.yaml
suite_runner
run_now
retry semantics
artifacts
markdown/html report
```

不实现：

```text
Cron daemon
multi-device pool
general parallel executor
report dashboard
```

### 门禁

- Suite 可以完整串行跑；
- `--run-now` 可触发；
- timeout_before_commit 行为正确；
- timeout_after_commit 不会重复支付；
- Retry History 可追溯；
- Report 数字来自真实 artifacts。

---

# 二十八、Round 5：分类 / 状态污染 / Flaky

完成三件事：

## A. 故障分类

至少真实得到：

```text
PRODUCT
DEVICE
AUTOMATION
```

如工程方便，再加入：

```text
ENVIRONMENT
```

## B. 并发状态污染实验

两个独立 Runner 同时操作共享状态。

不进入正式框架能力。

## C. Flaky 历史

同一 Case 连续 10–12 次。

生成：

```text
history.jsonl
```

以及简单摘要。

### 门禁

- 每个分类都有真实 evidence；
- Flaky 来自跨 Run 历史；
- 不人为修改结果文件凑数字；
- 报告能追溯原始 artifacts。

---

# 二十九、Round 6：工程 / 课件 / Runbook 对齐

这是正式冻结前必须执行的一轮。

Source of Truth 顺序：

```text
真实工程
   ↓
真实运行产物
   ↓
Runbook
   ↓
课件
```

绝不反过来。

重点检查至少包括：

```text
任务 YAML
Skill 名称
Suite YAML
Schedule YAML
失败分类
Self-Heal 顺序
Run Report 数字
Tool / Skill / Workflow 名称
```

课件中凡出现工程截图、配置、数字：

> 必须来自冻结后的真实工程。

---

# 三十、Codex 项目纪律

建议写入根目录 `AGENTS.md`。

1. 不得跨 Round 提前实现；
2. 每轮完成后必须 STOP 并报告；
3. 不得因为代码与测试都是自己写的就自行宣布验收通过；
4. 不允许 mock 真机执行结果；
5. 不允许生成从未真实执行过的 Run Report；
6. 课件引用数字必须来自真实 artifacts；
7. Self-Heal 不得直接修改正式资产；
8. Repair Candidate 必须经过 Review + Verify 才能 Write Back；
9. 所有 Demo 必须可 reset；
10. Self-Heal 的 writeback 必须可以 rollback；
11. 优先稳定与可解释，不追求平台完整度；
12. 每个课堂展示文件必须对应仓库真实文件；
13. **不得修改 `app/` 下的被测业务系统来让测试通过；**
14. 故意注入的 Product Bug 未经明确指令不得修复；
15. 不新增与课程目标无关的后台、控制台、管理页面；
16. 如果某一能力未真实运行通过，不得在 README / Report / Runbook 中写成已完成。

---

# 三十一、课堂安全策略

## Demo 0

准备：

- 原始自然语言用例；
- AI draft；
- 人工/规则 review 结果；
- 最终真实 task。

在线 LLM 如果超过预期时间：

> 使用预先保存的真实 draft 继续，不让课堂等待。

---

## Demo 1

准备：

- 正常 deterministic PASS artifacts；
- 设备锁屏/恢复成功 artifacts；
- deterministic FAIL artifacts；
-真实 Repair Candidate；
- Review 结果；
- Verify 结果；
- Write Back 后第二次 deterministic PASS。

如果在线 AI 临时失败：

> 可以从真实失败 evidence 直接打开上一轮生成的 Repair Candidate，继续演示治理链。

---

## Demo 2

不现场等待大量 Case。

流程：

1. 打开真实 Suite；
2. 打开真实 Run Plan；
3. 打开一次真实 Run Report；
4. 展开一个失败 evidence；
5. 现场 rerun 一个短 Case；
6. 展示 Retry History / Flaky History。

---

# 三十二、最终验收标准

## 真机

- USB iPhone 连接、设备信任与 Developer Mode 稳定；
- Appium 能连续建立 session；
- WebDriverAgent 能使用 Personal Team 签名并稳定启动；
- QuickTime 清晰；
- 实际会议软件共享可看清；
- Safari 系统权限弹窗处理片段稳定；
- reset 后设备回到 AVAILABLE。

## 被测系统

- UI V1/V2 可切换；
- timeout 两种模式稳定；
- Product Bug 可控；
- 所有状态可 reset。

## Demo 0

- AI draft 来自真实调用；
- 能明确指出 AI 缺失/臆造内容；
- 最终 task 来自真实工程。

## 单案例

- 连续执行至少 5 次；
- API + UI 双重验证；
- evidence 完整；
- cleanup 有效。

## Self-Heal

- 原资产必然 FAIL；
- Candidate 来自真实 AI；
- Candidate 不直接写回；
- Review 有结果；
- Verify 独立执行；
- Write Back 后 deterministic PASS；
- reset 可回滚资产。

## Suite / Retry / Report

- Suite 可 run-now；
- Retry 不会造成重复支付；
- Report 数字真实；
- Retry History 可追溯。

## Flaky

- 来自 10–12 次真实历史；
- 不是人为改结果；
- 能追溯每个 Run。

## 讲师

- 可以不依赖 Codex 跑 Demo 0；
- 可以不依赖 Codex 完整跑 Demo 1；
- 可以解释 Demo 2 的所有文件和 evidence；
- 知道每个故障的 reset 方法；
- 知道现场失败时的降级路径。

---

# 三十三、工期控制原则

不提前承诺固定 5–8 个工作日。

投入按门禁控制：

```text
Round 0 不通过 → 停
Round 0.5 不稳定 → 不做 AI
Round 1 不稳定 → 不做 Self-Heal
Round 2 不稳定 → 不扩 Suite
```

课堂项目的停止条件：

> **证据足够，就停止建设。**

而不是：

> “既然开始做框架，就把平台做完整。”

---

# 三十四、V2 冻结后的下一步

V2 审核通过后，不再让 Codex 阅读整份方案自由发挥。

实际施工方式：

```text
只给 Round 0 指令
↓
Codex 执行
↓
STOP
↓
独立验收
↓
通过后才发 Round 0.5
```

每轮指令必须包含：

- 本轮目标；
- 明确不做什么；
- 输入；
- 输出文件；
- 必须实际执行的验证；
- 验收门禁；
- STOP 输出格式。
