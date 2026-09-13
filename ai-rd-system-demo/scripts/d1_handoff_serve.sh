#!/usr/bin/env bash
# D1 工程现场接力：从 workspaces/d1-handoff 启动一个固定端口的本地服务，
# 供课堂直接在浏览器里看页面、点筛选、点导出——不依赖外网，只访问 127.0.0.1。
#
# 用法：./scripts/d1_handoff_serve.sh
# 固定端口可用 D1_HANDOFF_PORT 环境变量覆盖，默认 8010。
#
# --reload 会在 app/ 下的 Python 代码变化后自动重启服务；static/index.html 是
# 每次请求直接从磁盘读取，改完刷新浏览器就能看到，不需要重启服务。
# 如果某次改动刷新后页面没变化（极少数情况下 --reload 没触发），
# 回到这个终端按 Ctrl+C，再重新运行一次本脚本即可。
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
workspace="${repo_root}/workspaces/d1-handoff"
port="${D1_HANDOFF_PORT:-8010}"

if [ ! -d "${workspace}" ]; then
  echo "workspaces/d1-handoff 不存在，先运行 ./scripts/reset_d1_handoff.sh" >&2
  exit 1
fi

cd "${workspace}"
echo "D1 handoff 页面：http://127.0.0.1:${port}/"
echo "（workspace=${workspace}；Python 代码改动会自动重启，static/index.html 改动刷新浏览器即可）"
exec "${repo_root}/.venv/bin/python" -m uvicorn app.main:app --reload --port "${port}"
