#!/usr/bin/env bash
# 停止 demo3_serve.sh 启动的本地服务（按固定端口查找并结束进程）。
# 用法：./scripts/demo3_stop.sh
set -euo pipefail

port="${D3_DEV_PORT:-8030}"
pids="$(lsof -ti "tcp:${port}" || true)"

if [ -z "${pids}" ]; then
  echo "端口 ${port} 上没有找到运行中的服务"
  exit 0
fi

kill ${pids}
echo "已停止端口 ${port} 上的服务（pid: ${pids}）"
