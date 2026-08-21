# AI Test Execution System

当前工程包含：Round 0（iPhone 真机环境与投屏门禁）、Round 0.5（本地可控被测业务系统）、Round 1（Demo 0 资产与单条真机确定性用例）、Round 2（受控 locator Self-Heal）及 Round 3（Tool → Skill → Workflow）实现。不包含 Suite、调度、Retry 或报告功能。

链路为：Mac → USB iPhone → Xcode / WebDriverAgent → Appium + XCUITest → Mobile Safari → 最小静态页 → QuickTime 投屏 → 会议软件共享。

## 运行

先完成 [Personal Team 课前步骤](docs/ios-personal-team-setup.md)，再运行：

```bash
./scripts/preflight_ios.sh
IOS_UDID='<udid>' IOS_TEAM_ID='<team id>' python3 scripts/run_round0_ios.py
```

执行脚本会真实启动 Mac 静态页、以 XCUITest 创建 iPhone Safari session、点击按钮、断言页面状态变化并保存截图。QuickTime 的 iPhone 画面是否稳定显示需要人工视觉确认，具体步骤见课前文档。原始运行产物写入本机 `evidence/ios-<时间戳>/`，默认不提交；仓库只保留脱敏后的 Round 0 摘要。

`site/index.html` 还提供一个可选定位权限按钮，用于课堂证明 Safari 的系统权限弹窗不是 Web DOM；它不属于 Round 0 基础门禁。

## Round 0.5：本地被测业务系统

这是一个完全本地的 FastAPI Mock 业务世界：登录 → 待付款订单 → 付款 → 查询业务事实。不接真实支付或外部系统。

```bash
cd ai-test-execution-system
./scripts/reset_demo.sh
./scripts/start_demo.sh
```

浏览器或 iPhone Safari 访问 Mac 的局域网地址（例如 `http://<Mac-LAN-IP>:8000`）。页面上的固定课堂账号为 `course-demo`，无需密码。

常用 API：

```text
POST /api/reset
POST /api/test-data/prepare-pending-order
POST /api/login
GET  /api/orders
GET  /api/orders/{order_id}/facts
POST /api/orders/{order_id}/pay
GET  /api/config
PUT  /api/config
```

`PUT /api/config` 的 JSON 可控制 `ui_version`（`v1`/`v2`）、`payment_mode`（`normal`、`timeout_before_commit`、`timeout_after_commit`）和 `product_bug_mode`（`off`/`on`）。

`UI_VERSION=v2 ./scripts/start_demo.sh` 可在启动前把页面切为 V2；V1 的 `id="pay-now"` 在 V2 中不存在，V2 使用 `data-testid="confirm-payment"`。`PAYMENT_MODE` 和 `PRODUCT_BUG_MODE` 也可同样在启动前设置。重新运行 `./scripts/reset_demo.sh` 会恢复固定 baseline：V1、normal、Product Bug 关闭、一个待付款订单、库存 10、无 Payment。

`POST /api/test-data/prepare-pending-order` 只重建用户、商品、库存、订单与 Payment 等业务数据；它会保留当前 `ui_version`、`payment_mode` 与 `product_bug_mode`。只有 `POST /api/reset` / `./scripts/reset_demo.sh` 会恢复完整 baseline。

## Round 1：Demo 0 与真机支付用例

Demo 0 的自然语言输入、AI 初稿、审查说明与最终任务分别在 `demo0/` 和 `cases/pay_order.yaml`。最终 YAML 不是课件摆设：`scripts/run_pay_order_ios.py` 只读取它的 UI 步骤、V1 locator、API 断言和 cleanup 定义，不在运行时使用 AI 或修改 locator。

先在一个终端启动被测系统：

```bash
./scripts/reset_demo.sh
./scripts/start_demo.sh
```

再在另一个终端执行一次真机闭环（环境变量只在本机 shell 中设置）：

```bash
DEMO_BASE_URL='http://<Mac-LAN-IP>:8000' \
IOS_UDID='<iPhone-UDID>' IOS_TEAM_ID='<Personal-Team-ID>' \
IOS_WDA_BUNDLE_ID='<personal-WDA-bundle-id>' \
python3 scripts/run_pay_order_ios.py
```

稳定性门禁使用同一 YAML 连续执行五次：

```bash
DEMO_BASE_URL='http://<Mac-LAN-IP>:8000' \
IOS_UDID='<iPhone-UDID>' IOS_TEAM_ID='<Personal-Team-ID>' \
IOS_WDA_BUNDLE_ID='<personal-WDA-bundle-id>' \
python3 scripts/run_pay_order_ios.py --runs 5

python3 scripts/write_round1_pass_summary.py evidence/round1-<timestamp>/batch.json
```

每次执行均按 `reset → prepare → 真机 UI → API facts → cleanup` 完成。Round 3 中 runner 通过 `pay_order_and_verify` Workflow 调用 `skills/` 下的真实 Skill，再由 Skill 调用 `tools/` 下的原子 Tool。失败时保存截图、Appium/设备日志、当前步骤及可获得的 API facts；原始产物默认位于被忽略的 `evidence/round1-*`。

## Round 3：Tool → Skill → Workflow

Round 3 只整理已经验证的支付能力，不扩展业务范围：

- Tool：`tools/ui.py`、`tools/api.py`、`tools/device.py`，只执行原子动作，不改 locator、不重试、不调用 Self-Heal。
- Skill：`skills/` 下的 `prepare_pending_order`、`login`、`open_pending_order`、`pay_order`、`assert_business_state`、`reset_test_state`。
- Workflow：`workflows/pay_order_and_verify.py`，固定组合准备、登录、打开订单、UI 支付、API 四项事实和 cleanup。

冻结的任务契约见 [`docs/executable-task-schema-v1.md`](docs/executable-task-schema-v1.md)。`pay_order` 只证明 UI 交互和页面结果；`assert_business_state` 独立验证 `PAID`、Payment=1、`SUCCEEDED`、库存=9。

## Round 2：受控 UI locator Self-Heal

Round 2 只演示这一条边界：UI V2 令正式资产中的 `#pay-now` 真实失败，模型只给出 Candidate；确定性 Review、临时真机验证和 Write Back 负责控制风险。模型不会直接改动 `cases/pay_order.yaml`，运行时没有双 locator / fallback。

完整真实执行（系统在另一终端运行，iPhone 已解锁并满足 Round 1 真机前置条件）：

```bash
DEMO_BASE_URL='http://<Mac-LAN-IP>:8000' \
IOS_UDID='<iPhone-UDID>' IOS_TEAM_ID='<Personal-Team-ID>' \
IOS_WDA_BUNDLE_ID='<personal-WDA-bundle-id>' \
OPENAI_API_KEY='<only-in-local-shell>' \
python3 scripts/run_round2_self_heal.py
```

没有 API Key 时，不允许伪造本地候选。先在真实 failure 后停住（此命令仍会先跑 V1 baseline）：

```bash
python3 scripts/run_round2_self_heal.py --stop-after-failure
```

命令会打印本次 bundle 路径。用该路径运行 `scripts/render_round2_candidate_prompt.py`，把它输出的 failure context 和同目录截图交给交互式 Codex，并把其**真实输出**保存为仅含 `target`、`old_locator`、`candidate`、`evidence` 的 JSON；然后显式导入继续：

```bash
python3 scripts/run_round2_self_heal.py \
  --failure-dir evidence/round2-<timestamp>/v2-old-locator-failure \
  --interactive-candidate /path/to/real-interactive-candidate.json
```

导入产物会标记为 `interactive_codex_export`，不会伪装成 API 实时调用。两种来源都会经过相同的唯一匹配、固定 API facts、三次真机临时验证和单行 Write Back。通过后，脚本会用写回后的正式资产在 V2 再跑一次（不调用 AI），最后恢复 baseline 并再次制造旧 locator failure。

课堂恢复命令：

```bash
./scripts/restore_self_heal_baseline.sh
```

它只恢复正式 `pay_order` locator 为 `#pay-now`，并恢复 V1 / normal / Product Bug off、删除导入 Candidate；脱敏摘要和被 Git 忽略的运行 evidence 会保留供课后核验。`reset_demo.sh` 也会恢复此 locator，防止上一轮 Write Back 污染下次演示。
