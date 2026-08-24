#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -ne 0 ]]; then
  echo "此脚本不接受参数。用法: $0" >&2
  exit 1
fi

echo "============================================================"
echo " Appium 真机测试环境卸载"
echo "============================================================"
echo

if command -v appium >/dev/null 2>&1; then
  echo "Appium:"
  appium --version
  echo
  echo "Installed Drivers:"
  installed_drivers="$(appium driver list --installed 2>&1 || true)"
  echo "$installed_drivers"
else
  echo "Appium: SKIP（未找到 Appium）"
  installed_drivers=""
fi

echo
read -r -p "确认卸载？输入 RESET 继续: " confirm
if [[ "$confirm" != "RESET" ]]; then
  echo "已取消。"
  exit 0
fi

echo
echo "1. XCUITest Driver"
if command -v appium >/dev/null 2>&1 && grep -qiE '(^|[^[:alnum:]_-])xcuitest([^[:alnum:]_-]|$)' <<<"$installed_drivers"; then
  appium driver uninstall xcuitest
else
  echo "SKIP（未找到 xcuitest Driver）"
fi

echo
echo "2. Appium"
if command -v appium >/dev/null 2>&1; then
  npm uninstall -g appium
else
  echo "SKIP（未找到 Appium）"
fi

echo
echo "检查 Appium："
if command -v appium >/dev/null 2>&1; then
  echo "Appium 仍存在：$(command -v appium)"
  exit 1
else
  echo "Appium 不存在。"
fi

echo
echo "Appium environment: RESET"
echo
echo "Preserved:"
echo "- Node/npm"
echo "- Python"
echo "- Xcode"
echo "- Apple signing"
echo "- iPhone configuration"
echo "- WDA on device"
echo "- Test evidence and reports"
echo "- Project source code"
echo
echo "Next:"
echo "Ask Codex to rebuild Appium + XCUITest Driver."
