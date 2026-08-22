#!/usr/bin/env python3
"""Round 0 only: real iPhone Safari + Appium/XCUITest + screenshot gate."""
import base64
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from threading import Thread

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
EVIDENCE = ROOT / "evidence" / ("ios-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
PORT = 8000
ELEMENT_KEY = "element-6066-11e4-a52e-4f735466cecf"

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass

record = {"round": "Round 0", "platform": "iOS", "started_at": datetime.now(timezone.utc).isoformat(),
          "commands": [], "result": "FAIL"}

def run(*command):
    completed = subprocess.run(command, text=True, capture_output=True)
    record["commands"].append({"command": list(command), "exit_code": completed.returncode,
                               "stdout": completed.stdout, "stderr": completed.stderr})
    return completed

def webdriver(method, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request("http://127.0.0.1:4723" + path, data=data, method=method,
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=90) as response:
        return json.loads(response.read().decode())["value"]

def lan_ip():
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("8.8.8.8", 80))
        return probe.getsockname()[0]
    finally:
        probe.close()

appium = None
appium_log = None
session_id = None
server = None
try:
    EVIDENCE.mkdir(parents=True)
    udid = os.environ.get("IOS_UDID")
    team_id = os.environ.get("IOS_TEAM_ID")
    wda_bundle_id = os.environ.get("IOS_WDA_BUNDLE_ID")
    if not udid:
        raise RuntimeError("请设置 IOS_UDID 为 Xcode 发现的 iPhone UDID。")
    if not team_id:
        raise RuntimeError("请设置 IOS_TEAM_ID 为 Apple Personal Team ID；不得将其写入项目文件。")
    for binary in ("python3", "node", "npm", "appium", "xcodebuild", "xcrun"):
        if not shutil.which(binary):
            raise RuntimeError(f"缺少命令: {binary}")
    run("python3", "--version")
    run("node", "--version")
    run("npm", "--version")
    if run("xcodebuild", "-version").returncode:
        raise RuntimeError("需要完整 Xcode，当前开发者目录不能仅为 Command Line Tools。")
    run("appium", "--version")
    drivers = run("appium", "driver", "list", "--installed")
    if "xcuitest" not in drivers.stdout + drivers.stderr:
        raise RuntimeError("未安装 Appium XCUITest Driver。")
    device_info = run("xcrun", "devicectl", "device", "info", "details", "--device", udid)
    if device_info.returncode:
        raise RuntimeError("Xcode 无法访问此 iPhone；请检查 USB 信任、Developer Mode 和连接状态。")
    os.chdir(SITE)
    server = ThreadingHTTPServer(("0.0.0.0", PORT), QuietHandler)
    Thread(target=server.serve_forever, daemon=True).start()
    host_ip = lan_ip()
    test_url = f"http://{host_ip}:{PORT}/index.html"
    record["test_page"] = test_url
    with urllib.request.urlopen("http://127.0.0.1:8000/index.html", timeout=5) as response:
        record["mac_test_page_http_status"] = response.status
    appium_log = (EVIDENCE / "appium.log").open("w")
    appium = subprocess.Popen(["appium", "--address", "127.0.0.1", "--port", "4723"], stdout=appium_log,
                              stderr=subprocess.STDOUT, text=True)
    for _ in range(20):
        try:
            webdriver("GET", "/status")
            break
        except (urllib.error.URLError, TimeoutError):
            time.sleep(1)
    else:
        raise RuntimeError("Appium 未能在 4723 端口启动。")
    caps = {"capabilities": {"alwaysMatch": {"platformName": "iOS", "browserName": "Safari",
            "appium:automationName": "XCUITest", "appium:udid": udid,
            "appium:xcodeOrgId": team_id, "appium:xcodeSigningId": "Apple Development",
            "appium:newCommandTimeout": 120, "appium:webviewConnectTimeout": 30000,
            "appium:showXcodeLog": True}, "firstMatch": [{}]}}
    if wda_bundle_id:
        caps["capabilities"]["alwaysMatch"]["appium:updatedWDABundleId"] = wda_bundle_id
    created = webdriver("POST", "/session", caps)
    session_id = created["sessionId"]
    record["appium_session"] = session_id
    webdriver("POST", f"/session/{session_id}/url", {"url": test_url})
    button = webdriver("POST", f"/session/{session_id}/element", {"using": "css selector", "value": "#round0-action"})
    webdriver("POST", f"/session/{session_id}/element/{button[ELEMENT_KEY]}/click", {})
    status = webdriver("POST", f"/session/{session_id}/element", {"using": "css selector", "value": "#status"})
    text = webdriver("GET", f"/session/{session_id}/element/{status[ELEMENT_KEY]}/text")
    if text != "已由 Appium 点击验证":
        raise RuntimeError(f"页面状态未变化，实际值: {text!r}")
    time.sleep(1)
    (EVIDENCE / "after-click.png").write_bytes(base64.b64decode(webdriver("GET", f"/session/{session_id}/screenshot")))
    record["page_change"] = text
    record["quicktime"] = "需人工按 docs/ios-personal-team-setup.md 验证 USB 画面稳定显示"
    record["result"] = "PASS (automation); QuickTime requires human visual confirmation"
except Exception as error:
    record["error"] = str(error)
finally:
    if session_id:
        try:
            webdriver("DELETE", f"/session/{session_id}")
        except Exception:
            pass
    if appium:
        appium.terminate()
        try:
            appium.wait(timeout=5)
        except subprocess.TimeoutExpired:
            appium.kill()
    if appium_log:
        appium_log.close()
    if server:
        server.shutdown()
        server.server_close()
    record["finished_at"] = datetime.now(timezone.utc).isoformat()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / "run.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(record, ensure_ascii=False, indent=2))
    sys.exit(0 if record["result"].startswith("PASS") else 1)
