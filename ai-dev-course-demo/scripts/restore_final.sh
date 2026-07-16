#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! git -C "$ROOT_DIR" show-ref --verify --quiet refs/heads/main; then
  echo "未找到本地 main 分支。" >&2
  exit 1
fi

git -C "$ROOT_DIR" switch main
echo "已安全切回 main；未丢弃或清理本地修改。"
