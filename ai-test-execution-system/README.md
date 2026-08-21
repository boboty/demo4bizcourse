# AI Test Execution System

当前完成的范围：Round 0（iPhone 真机环境与投屏门禁）及 Round 0.5（本地可控被测业务系统）。不包含 Round 1 及后续的自动化用例、Agent、自愈、Suite、调度或报告功能。

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
