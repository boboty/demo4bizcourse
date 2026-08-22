#!/usr/bin/env bash
set -euo pipefail
git checkout demo2/reference -- app/financing/service.py app/main.py static/index.html docs/api.md
echo "restored Demo 2 reference solution"
pytest -q
python instructor/checks/task_a_acceptance.py
