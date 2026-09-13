#!/usr/bin/env bash
# D4 页面：从 workspaces/demo4-sedimentation 启动一个固定端口的本地服务，
# 供课堂在浏览器里看融资申请页面、点"放款处理导出"——只访问 127.0.0.1。
#
# 用法：./scripts/demo4_serve.sh
# 固定端口可用 D4_DEV_PORT 环境变量覆盖，默认 8050。
#
# --reload 会在 app/ 下的 Python 代码变化后自动重启服务（inject_demo4_regression.sh /
# restore_demo4_fixed.sh 改完代码不需要手动重启）；static/index.html 每次请求直接从磁盘读取，
# 改完刷新浏览器就能看到。
set -euo pipefail

repo_root="$(cd "$(dirname "${0}")/.." && pwd)"
workspace="${repo_root}/workspaces/demo4-sedimentation"
port="${D4_DEV_PORT:-8050}"

if [ ! -d "${workspace}" ]; then
  echo "workspaces/demo4-sedimentation 不存在，先运行 ./scripts/reset_demo4.sh" >&2
  exit 1
fi

cd "${workspace}"
echo "D4 页面：http://127.0.0.1:${port}/"
echo "（workspace=${workspace}；Python 代码改动会自动重启，static/index.html 改动刷新浏览器即可）"
exec "${repo_root}/.venv/bin/python" -m uvicorn app.main:app --reload --port "${port}"
