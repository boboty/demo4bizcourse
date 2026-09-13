#!/usr/bin/env bash
# D3 独立验收：独立算出期望结果，通过 workspaces/demo3-validator/bin/actual-output
# 这一个黑盒 HTTP 入口取得运行中开发服务的实际输出并比较。
#
# 用法：./scripts/demo3_validator.sh [base_url]
# 先运行 ./scripts/demo3_serve.sh 起开发服务，默认访问 http://127.0.0.1:8030。
set -euo pipefail

repo_root="$(cd "$(dirname "${0}")/.." && pwd)"
base_url="${1:-http://127.0.0.1:8030}"

exec "${repo_root}/.venv/bin/python" "${repo_root}/scripts/demo3_validator.py" --base-url "${base_url}"
