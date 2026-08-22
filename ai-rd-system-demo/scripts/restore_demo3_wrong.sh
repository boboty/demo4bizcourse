#!/usr/bin/env bash
set -euo pipefail
git checkout demo/base -- app/settlement/service.py tests/test_settlement_developer.py AGENTS.md validation/checklist.md
echo "restored Demo 3 wrong/full-green state"
pytest -q tests/test_settlement_developer.py
