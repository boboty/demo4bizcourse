# AI Test Execution System — Round 0（iOS）

本目录只包含 iPhone 真机的 Round 0 环境与投屏门禁；不含任何 Round 0.5 或后续业务功能，也不包含正式 FastAPI 业务系统。

链路为：Mac → USB iPhone → Xcode / WebDriverAgent → Appium + XCUITest → Mobile Safari → 最小静态页 → QuickTime 投屏 → 会议软件共享。

## 运行

先完成 [Personal Team 课前步骤](docs/ios-personal-team-setup.md)，再运行：

```bash
./scripts/preflight_ios.sh
IOS_UDID='<udid>' IOS_TEAM_ID='<team id>' python3 scripts/run_round0_ios.py
```

执行脚本会真实启动 Mac 静态页、以 XCUITest 创建 iPhone Safari session、点击按钮、断言页面状态变化并保存截图。QuickTime 的 iPhone 画面是否稳定显示需要人工视觉确认，具体步骤见课前文档。原始运行产物写入本机 `evidence/ios-<时间戳>/`，默认不提交；仓库只保留脱敏后的 Round 0 摘要。

`site/index.html` 还提供一个可选定位权限按钮，用于课堂证明 Safari 的系统权限弹窗不是 Web DOM；它不属于 Round 0 基础门禁。
