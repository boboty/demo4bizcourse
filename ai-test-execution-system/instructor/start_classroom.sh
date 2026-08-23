#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
PYTHON_BIN=${PYTHON_BIN:-python3}
SERVER_URL='http://127.0.0.1:8765'

cd "$PROJECT_DIR"

"$PYTHON_BIN" "$SCRIPT_DIR/classroom_runbook_server.py" &
SERVER_PID=$!

cleanup() {
  trap - INT TERM EXIT
  kill "$SERVER_PID" 2>/dev/null || true
  wait "$SERVER_PID" 2>/dev/null || true
}
trap cleanup INT TERM EXIT

ready=0
attempt=0
while [ "$attempt" -lt 50 ]; do
  if "$PYTHON_BIN" -c 'import sys, urllib.request; urllib.request.urlopen(sys.argv[1], timeout=1).read()' "$SERVER_URL/api/runtime" >/dev/null 2>&1; then
    ready=1
    break
  fi
  attempt=$((attempt + 1))
  sleep 0.1
done

if [ "$ready" -ne 1 ]; then
  echo "Classroom Runbook did not become ready at $SERVER_URL" >&2
  exit 1
fi

echo "Opening $SERVER_URL/"
open "$SERVER_URL/"
wait "$SERVER_PID"
