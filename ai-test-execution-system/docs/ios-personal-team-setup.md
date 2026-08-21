# iOS 真机 Round 0：Personal Team 课前步骤

本步骤只使用免费的 Apple Personal Team。不要向任何脚本、文档或他人提供 Apple ID 密码、双重验证验证码或私钥。

1. 在 Mac 安装完整 Xcode，首次启动后接受许可；在 Xcode 的 **Settings → Accounts** 中由授课者自行登录 Apple ID。
2. USB 连接 iPhone、解锁，并在 iPhone 的“信任此电脑”提示中选择信任。
3. 在 iPhone 的“设置 → 隐私与安全性 → 开发者模式”中启用 Developer Mode，并按设备提示重启确认。
4. 在终端运行 `scripts/preflight_ios.sh`。Xcode 能列出该 iPhone 后，记录其 UDID；不要把 UDID 或 Team ID 提交到项目中。
5. 使用 `appium driver run xcuitest open-wda` 打开 WebDriverAgent 工程。选择 `WebDriverAgentRunner` target，在 **Signing & Capabilities** 中选择自己的 Personal Team，并让 Xcode 自动管理签名。若 Bundle Identifier 冲突，改为自己唯一的反向域名。
6. 选择已连接 iPhone，运行 `WebDriverAgentRunner` 一次。若 iPhone 提示开发者不受信任，在“设置 → 通用 → VPN 与设备管理”中由设备所有者信任该开发者证书，然后再次运行，确认测试成功。
7. 运行 `IOS_UDID='<udid>' IOS_TEAM_ID='<team id>' python3 scripts/run_round0_ios.py`。iPhone 与 Mac 必须处于同一局域网，Safari 必须能访问脚本输出的 `http://<Mac-LAN-IP>:8000/index.html`。
8. QuickTime：打开 **QuickTime Player → 文件 → 新建影片录制**，点击录制按钮旁箭头，在“相机”中选择 iPhone；确认画面持续显示至少 10 秒。会议软件中选择“共享屏幕”，共享 QuickTime 窗口即可。

定位按钮是可选的系统层 UI 演示：Safari 的定位权限弹窗由 iOS 提供，不属于普通 Web DOM。它不属于 Round 0 的基础通过条件；在 Safari 对非 HTTPS 页限制定位时，请勿将失败误判为 WDA 失败。
