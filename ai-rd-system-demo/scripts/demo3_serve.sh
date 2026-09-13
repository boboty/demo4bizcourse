#!/usr/bin/env bash
# D3 开发方页面：从 workspaces/demo3-developer 启动一个固定端口的本地服务，
# 供课堂在浏览器里看页面、点筛选、点"放款处理导出"——只访问 127.0.0.1。
#
# 用法：./scripts/demo3_serve.sh
# 固定端口可用 D3_DEV_PORT 环境变量覆盖，默认 8030。
# 独立 Validator 的 bin/actual-output 默认也访问这个端口，改端口时两边要一起改。
#
# --reload 会在 app/ 下的 Python 代码变化后自动重启服务；static/index.html 是
# 每次请求直接从磁盘读取，改完刷新浏览器就能看到，不需要重启服务。
set -euo pipefail

repo_root="$(cd "$(dirname "${0}")/.." && pwd)"
workspace="${repo_root}/workspaces/demo3-developer"
port="${D3_DEV_PORT:-8030}"

if [ ! -d "${workspace}" ]; then
  echo "workspaces/demo3-developer 不存在，先运行 ./scripts/reset_demo3_developer.sh" >&2
  exit 1
fi

cd "${workspace}"
echo "D3 开发方页面：http://127.0.0.1:${port}/"
echo "（workspace=${workspace}；Python 代码改动会自动重启，static/index.html 改动刷新浏览器即可）"
exec "${repo_root}/.venv/bin/python" -m uvicorn app.main:app --reload --port "${port}"
