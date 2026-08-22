#!/usr/bin/env bash
# Round 0 iOS preflight. It never signs code or requests Apple credentials.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date +%Y%m%d-%H%M%S)"
EVIDENCE_DIR="$ROOT/evidence/ios-$STAMP"
LOG="$EVIDENCE_DIR/preflight.log"
mkdir -p "$EVIDENCE_DIR"

status=0
check() {
  local name="$1"; shift
  {
    printf '\n$'; printf ' %q' "$@"; printf '\n'
    "$@"
  } >>"$LOG" 2>&1
  local code=$?
  if [ "$code" -eq 0 ]; then
    printf 'PASS  %s\n' "$name" | tee -a "$LOG"
  else
    printf 'FAIL  %s (exit %s)\n' "$name" "$code" | tee -a "$LOG"
    status=1
  fi
}

check "Python" python3 --version
check "Node" node --version
check "npm" npm --version
check "完整 Xcode（非 Command Line Tools）" xcodebuild -version
check "Appium" appium --version
check "XCUITest Driver" sh -c 'appium driver list --installed 2>&1 | grep -i xcuitest'
check "XCUITest / WebDriverAgent 非签名依赖" appium driver doctor xcuitest
check "QuickTime Player" test -d "/System/Applications/QuickTime Player.app"

if xcodebuild -version >>"$LOG" 2>&1; then
  check "iPhone USB / Xcode device discovery" xcrun devicectl list devices
  printf '\nINFO  请确认上述设备状态为 connected/available。Developer Mode、信任和 WDA 签名只能由真实 session 最终验证。\n' | tee -a "$LOG"
else
  printf '\nSKIP  未安装或未选中完整 Xcode，无法检查 iPhone、Developer Mode 和 WebDriverAgent。\n' | tee -a "$LOG"
  status=1
fi

printf '\n证据文件：%s\n' "$LOG" | tee -a "$LOG"
exit "$status"
