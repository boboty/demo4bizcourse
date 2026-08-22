# Round 6A Classroom Preflight

所有时间点都使用本机环境，不把设备标识、Team ID、LAN IP、session id 或原始 evidence 写入仓库。

## T-2 days

- [ ] Xcode 登录和 Personal Team 可用；确认签名时效。
- [ ] iPhone Developer Mode、USB trust、解锁状态正常。
- [ ] 重新 Build/Sign WebDriverAgent；确认 Appium XCUITest 可建立真机 session。
- [ ] iPhone Safari 可访问本地 FastAPI 页面。
- [ ] QuickTime 可投屏；准备 USB 线和充电。
- [ ] 完整排练 Demo 1：baseline → V2 failure → Candidate → Review → Verify → Write Back → AI-off PASS → restore。

```bash
cd ai-test-execution-system
./scripts/preflight_ios.sh
./scripts/reset_demo.sh
```

## T-1 day

- [ ] 完整跑一次 Round 2；保留真实 Candidate 的本机备用文件。
- [ ] 确认 Failure Bundle 中有 `failure-context.json`、`page-source.html`、截图和 Appium log。
- [ ] 确认 Candidate verification 是真实 3/3 evidence；没有就使用已经保存的真实结果并标注 fallback。
- [ ] 确认 `./scripts/restore_self_heal_baseline.sh` 能恢复 `#pay-now`、V1、normal、Product Bug off。
- [ ] 确认 Demo 2 的脱敏摘要和 Round 5 summary 可打开；不依赖 GitHub 原始 artifacts。

## T-30 min

- [ ] 启动 FastAPI：`./scripts/start_demo.sh`。
- [ ] 检查 `http://<MAC-LAN-IP>:8000/health` 返回 `{"status":"ok"}`。
- [ ] iPhone 可打开 Safari 页面；关闭旧标签页或缓存影响。
- [ ] Appium 与 XCUITest driver 正常；QuickTime 投屏窗口可见。
- [ ] iPhone 连接充电、关闭自动锁屏/通知干扰，保持 Developer Mode。
- [ ] 执行 `./scripts/reset_demo.sh`，确认正式 locator 为 `#pay-now`。

## T-5 min

只做最短 gate：

```bash
curl -fsS http://<MAC-LAN-IP>:8000/health
appium --version
./scripts/restore_self_heal_baseline.sh
```

- [ ] 设备在 `xcrun devicectl list devices` 中可见。
- [ ] Safari 已打开 Demo 页面。
- [ ] QuickTime 投屏正常。
- [ ] baseline locator 已恢复。

T-5 min 不再运行完整 Round 2、完整 iPhone Suite 或新的 Candidate 生成。
