#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# reset_appium_env.sh
#
# 课堂安全复位：清除本 Demo 的 Appium 运行环境，但保留基础开发环境。
#
# 默认：
#   ./scripts/reset_appium_env.sh
#
# 连同全局 Appium 和用户级 Driver 一起删除：
#   ./scripts/reset_appium_env.sh --global
#
# 进一步清理本机 WDA 构建缓存：
#   ./scripts/reset_appium_env.sh --deep
# ============================================================

REMOVE_GLOBAL=false
DEEP=false

for arg in "$@"; do
  case "$arg" in
    --global)
      REMOVE_GLOBAL=true
      ;;
    --deep)
      DEEP=true
      ;;
    *)
      echo "未知参数: $arg" >&2
      echo "用法: $0 [--global] [--deep]" >&2
      exit 1
      ;;
  esac
done

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEMO_APPIUM_HOME="${APPIUM_HOME:-$PROJECT_ROOT/.appium}"

# 只允许清理明确的 Appium 目录，避免误把项目根目录或用户目录当作目标。
if [[ "$DEMO_APPIUM_HOME" != /* || "$DEMO_APPIUM_HOME" == "/" || "$DEMO_APPIUM_HOME" == "$HOME" || "$DEMO_APPIUM_HOME" == "$PROJECT_ROOT" ]]; then
  echo "APPIUM_HOME 必须是安全的绝对路径，且不能是根目录、用户目录或项目目录。" >&2
  exit 1
fi

echo
echo "============================================================"
echo " Appium 真机测试环境复位"
echo "============================================================"
echo
echo "项目目录:       $PROJECT_ROOT"
echo "APPIUM_HOME:    $DEMO_APPIUM_HOME"
echo "删除全局 Appium: $REMOVE_GLOBAL"
echo "深度清理 WDA:   $DEEP"
echo
echo "【保留】"
echo "  ✓ Homebrew"
echo "  ✓ Node.js / npm"
echo "  ✓ Python / 项目 .venv"
echo "  ✓ Xcode / Command Line Tools"
echo "  ✓ Apple Signing / Certificates"
echo "  ✓ iPhone Trust / Developer Mode"
echo "  ✓ iPhone 上已经安装的 WebDriverAgentRunner"
echo
echo "【将清理】"
echo "  - Appium、iproxy、WebDriverAgent 相关进程"
echo "  - Demo 项目的 APPIUM_HOME 和 node_modules（若存在）"
echo "  - Demo 的本机运行证据、artifacts、reports 和临时 Candidate"
if $REMOVE_GLOBAL; then
  echo "  - 全局 npm Appium"
  echo "  - 用户级 ~/.appium Driver / Plugin 环境"
fi
if $DEEP; then
  echo "  - Xcode WebDriverAgent DerivedData / 构建缓存"
fi

echo
read -r -p "确认执行？输入 RESET 继续: " CONFIRM
if [[ "$CONFIRM" != "RESET" ]]; then
  echo "已取消。"
  exit 0
fi

echo
echo "1. 停止 Appium / WDA 相关进程..."

# 只匹配 Appium 可执行文件名或其安装路径，避免匹配到当前脚本自身。
pkill -x appium 2>/dev/null || true
pkill -f '/appium([ /]|$)' 2>/dev/null || true
pkill -f '[i]proxy' 2>/dev/null || true
pkill -f '[W]ebDriverAgent' 2>/dev/null || true
echo "   完成。"

echo
echo "2. 清理 Demo 项目环境..."

rm -rf -- "$DEMO_APPIUM_HOME"
rm -rf -- "$PROJECT_ROOT/node_modules"
rm -rf -- "$PROJECT_ROOT/.pytest_cache"
rm -rf -- "$PROJECT_ROOT/self_heal/candidates"/*.json

# 仅删除本机运行目录；脱敏的 pass summary 是仓库资产，保留不动。
remove_top_level_dirs() {
  local parent="$1"
  [[ -d "$parent" ]] || return 0
  while IFS= read -r -d '' path; do
    rm -rf -- "$path"
  done < <(find "$parent" -mindepth 1 -maxdepth 1 -type d -print0)
}

remove_top_level_dirs "$PROJECT_ROOT/evidence"
remove_top_level_dirs "$PROJECT_ROOT/artifacts"
remove_top_level_dirs "$PROJECT_ROOT/reports"

for runtime_dir in output results screenshots logs; do
  rm -rf -- "$PROJECT_ROOT/$runtime_dir"
done
echo "   完成。"

if $REMOVE_GLOBAL; then
  echo
  echo "3. 删除全局 Appium..."
  if command -v npm >/dev/null 2>&1; then
    if npm list -g appium --depth=0 >/dev/null 2>&1; then
      npm uninstall -g appium || true
    else
      echo "   未发现全局 npm Appium。"
    fi
  else
    echo "   未找到 npm，跳过全局 npm Appium。"
  fi

  if [[ -d "$HOME/.appium" ]]; then
    rm -rf -- "$HOME/.appium"
    echo "   已删除 ~/.appium"
  fi
  echo "   完成。"
else
  echo
  echo "3. 跳过全局 Appium。"
fi

if $DEEP; then
  echo
  echo "4. 深度清理 WebDriverAgent 构建缓存..."
  DERIVED_DATA="$HOME/Library/Developer/Xcode/DerivedData"
  if [[ -d "$DERIVED_DATA" ]]; then
    find "$DERIVED_DATA" \
      -maxdepth 1 \
      -type d \
      \( -name 'WebDriverAgent-*' -o -name 'WebDriverAgentRunner-*' \) \
      -print \
      -exec rm -rf -- {} + 2>/dev/null || true
  fi

  if [[ -d "$HOME/Library/Caches" ]]; then
    find "$HOME/Library/Caches" \
      -maxdepth 1 \
      -type d \
      -name 'appium*' \
      -print \
      -exec rm -rf -- {} + 2>/dev/null || true
  fi
  echo "   完成。"
else
  echo
  echo "4. 跳过 WDA 深度清理。"
fi

echo
echo "============================================================"
echo " 复位完成"
echo "============================================================"
echo
echo "基础环境检查："

for cmd in brew node npm python3 xcodebuild; do
  if command -v "$cmd" >/dev/null 2>&1; then
    printf '  ✓ %-12s ' "$cmd"
    case "$cmd" in
      node) node --version ;;
      npm) npm --version ;;
      python3) python3 --version ;;
      xcodebuild) xcodebuild -version | head -1 ;;
      brew) brew --version | head -1 ;;
    esac
  else
    echo "  ! $cmd 未找到"
  fi
done

echo
echo "Appium 状态："
if command -v appium >/dev/null 2>&1; then
  echo "  ! PATH 中仍能找到 Appium："
  command -v appium
  appium --version 2>/dev/null || true
else
  echo "  ✓ PATH 中未找到 Appium"
fi

echo
echo "现在可以重新执行："
echo "  ./scripts/preflight_ios.sh"
echo "  IOS_UDID='<udid>' IOS_TEAM_ID='<team id>' python3 scripts/run_round0_ios.py"
