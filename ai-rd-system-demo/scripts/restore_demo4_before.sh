#!/usr/bin/env bash
set -euo pipefail
git checkout demo/base -- AGENTS.md validation/checklist.md
echo "restored Demo 4 before-learning state"
