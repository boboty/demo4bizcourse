#!/usr/bin/env bash
set -euo pipefail
name="${1:-capture}"
mkdir -p instructor/captures
git diff -- . ':(exclude)instructor/captures' > "instructor/captures/${name}.patch"
echo "saved instructor/captures/${name}.patch"
