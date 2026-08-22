#!/usr/bin/env bash
set -euo pipefail
git checkout demo3/fixed -- app/settlement/service.py tests/test_settlement_developer.py
echo "restored Demo 3 fixed state"
pytest -q tests/test_settlement_developer.py
python validation/independent_check.py
