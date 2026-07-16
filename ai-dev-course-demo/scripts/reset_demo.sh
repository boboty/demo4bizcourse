#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! git -C "$ROOT_DIR" rev-parse --verify demo-baseline >/dev/null 2>&1; then
  echo "未找到 demo-baseline 检查点。" >&2
  exit 1
fi

git -C "$ROOT_DIR" switch --discard-changes --detach demo-baseline
git -C "$ROOT_DIR" clean -fd -- app tests scripts
echo "已恢复到干净的 demo-baseline；.venv 已保留。"
echo "演示完成后可运行：./scripts/restore_final.sh"
