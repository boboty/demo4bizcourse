# 4-Demo Classroom Preflight

所有 Python 命令统一使用项目 `.venv`。任何新 Terminal 都先执行：

```bash
source .venv/bin/activate
```

不把设备标识、Team ID、LAN IP、session id 或原始 evidence 写入仓库。`evidence/`、`artifacts/runs/` 和其他运行日志按 `AGENTS.md` 规则作为 ignored runtime。

## T-2 days

- [ ] 确认项目 `.venv` 已准备；首次准备执行 `python -m pip install -r requirements.txt`。
- [ ] 用 `.venv` 执行 `python -m pytest` 和 `git diff --check`。
- [ ] Xcode Personal Team 可用，确认 WDA signing freshness；重新 Build/Sign WebDriverAgent。
- [ ] iPhone Developer Mode、USB trust、解锁状态正常。
- [ ] 保留并完整执行 `./scripts/preflight_ios.sh`。
- [ ] 完整排练 Demo 1 Round0：Appium/XCUITest Driver load Gate → `appium driver run xcuitest open-wda` → Xcode `Product → Test` → 停止 Xcode Test → 8000/4723 检查 → `run_round0_ios.py` → Safari 点击和 screenshot evidence → QuickTime 人工确认。
- [ ] 确认 Round0 期间没有提前启动 FastAPI 或独立 Appium；Round0 会占用 8000 和 4723。
- [ ] Demo 2 API 三场景完整：`normal`、`timeout-before`、`timeout-after`；确认 stdout 中出现各自的 HTTP 504、业务 facts 和 Retry 判断。
- [ ] Demo 3 Self-Heal 完整：business baseline → V1/V2 old locator failure → Failure Bundle → real Candidate → Review / Policy Gate → Verify 3/3 → Write Back → AI-off rerun → restore。
- [ ] Demo 4 的脱敏 evidence、report 和 artifact 可打开；不修改既有真实 evidence 数字。

首次准备示例（只在 `.venv` 尚不存在时创建）：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## T-30 min

Demo 1 Round0 尚未完成时，不要启动 FastAPI：

- [ ] 不执行 `./scripts/start_demo.sh`，不提前占用 8000。
- [ ] 不启动独立 Appium，不提前占用 4723。
- [ ] 新 Terminal source `.venv` 后确认端口可用；若占用只定位进程，不盲杀：

  ```bash
  source .venv/bin/activate
  lsof -nP -iTCP:8000 -sTCP:LISTEN
  lsof -nP -iTCP:4723 -sTCP:LISTEN
  ```

- [ ] QuickTime、iPhone、Xcode、Appium 都已 ready；iPhone 已连接、解锁并可投屏。
- [ ] Appium 启动时人工观察 XCUITest Driver 必须真实 load 成功；`Could not load driver` → STOP。

## Demo 1 完成以后

只有 Round0 完整、Xcode Test 已停止、screenshot evidence 已保存并完成 QuickTime 人工确认后，才启动 FastAPI：

```bash
source .venv/bin/activate
./scripts/reset_demo.sh
./scripts/start_demo.sh
```

- [ ] `curl -fsS http://127.0.0.1:8000/health` 成功。
- [ ] `curl -fsS http://<MAC-LAN-IP>:8000/health` 成功。
- [ ] iPhone Safari 能访问 `http://<MAC-LAN-IP>:8000/`。
- [ ] FastAPI 保持运行供 Demo 3 使用。

## T-5 min

T-5 不写成“FastAPI 一定已经启动”。上午 Demo 1 需要先使用 8000；T-5 只做不依赖该假设的最短检查：

```bash
source .venv/bin/activate
appium --version
xcrun devicectl list devices
./scripts/restore_self_heal_baseline.sh
```

- [ ] 不运行完整 Round0、完整 iPhone Suite 或新的 Candidate 生成。
- [ ] 设备在 `xcrun devicectl list devices` 中可见。
- [ ] QuickTime 投屏窗口、Xcode、Appium ready。
- [ ] baseline locator 已恢复为 `#pay-now`。
- [ ] 如果已经完成 Demo 1，按“Demo 1 完成以后”检查 FastAPI local + LAN `/health`；如果尚未完成，不启动 FastAPI。
