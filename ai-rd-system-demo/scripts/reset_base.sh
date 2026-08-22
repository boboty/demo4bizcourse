#!/usr/bin/env bash
set -euo pipefail
git reset --hard demo/base
git clean -fd -e .venv/ -e instructor/captures/
echo "restored demo/base"
