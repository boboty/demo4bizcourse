#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
VENV_PYTHON="$VENV_DIR/bin/python"

is_usable_venv() {
  [[ -d "$VENV_DIR" && ! -L "$VENV_DIR" && -x "$VENV_PYTHON" ]] \
    && "$VENV_PYTHON" -c \
      'import sys; raise SystemExit(sys.version_info < (3, 11) or sys.prefix == sys.base_prefix)'
}

if is_usable_venv; then
  echo "复用现有 Python 3.11+ 虚拟环境：$VENV_DIR"
else
  PYTHON_BIN=""
  if ! command -v uv >/dev/null 2>&1; then
    for candidate in python3.13 python3.12 python3.11 python3; do
      if command -v "$candidate" >/dev/null 2>&1 \
        && "$candidate" -c 'import sys; raise SystemExit(sys.version_info < (3, 11))'; then
        PYTHON_BIN="$candidate"
        break
      fi
    done

    if [[ -z "$PYTHON_BIN" ]]; then
      echo "需要 Python 3.11+；也可以先安装 uv。" >&2
      exit 1
    fi
  fi

  if [[ -e "$VENV_DIR" || -L "$VENV_DIR" ]]; then
    echo "现有 .venv 缺失或不兼容，正在安全重建。"
    if [[ -d "$VENV_DIR" && ! -L "$VENV_DIR" ]]; then
      rm -rf -- "$VENV_DIR"
    else
      rm -f -- "$VENV_DIR"
    fi
  fi

  if command -v uv >/dev/null 2>&1; then
    uv venv --python 3.11 "$VENV_DIR"
  else
    "$PYTHON_BIN" -m venv "$VENV_DIR"
  fi

  if ! is_usable_venv; then
    echo "未能创建有效的 Python 3.11+ 虚拟环境。" >&2
    exit 1
  fi
fi

if command -v uv >/dev/null 2>&1; then
  uv pip install --python "$VENV_PYTHON" -r "$ROOT_DIR/requirements.txt"
else
  if ! "$VENV_PYTHON" -m pip --version >/dev/null 2>&1; then
    "$VENV_PYTHON" -m ensurepip --upgrade
  fi
  "$VENV_PYTHON" -m pip install -r "$ROOT_DIR/requirements.txt"
fi
