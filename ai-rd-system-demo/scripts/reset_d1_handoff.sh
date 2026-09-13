#!/usr/bin/env bash
# 重建 D1 工程现场接力 demo 的固定"中途接手"起点：workspaces/d1-handoff。
#
# 用两层冻结快照（stage-0 → stage-1）重放出真实的 Git 历史：
#   1) 任务开始：baseline + TASK/PROGRESS/DECISIONS/feature-list 脚手架
#   2) 客户名称筛选完成：代码 + 测试 + 进度/决策更新
#   3) 空提交标记"上一个 session 已结束"
# 每次运行都会丢弃 workspaces/d1-handoff 里的旧状态，重新生成同样的历史。
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
baseline_root="$repo_root/instructor/baselines/d1-handoff"
workspace="$repo_root/workspaces/d1-handoff"

rm -rf "$workspace"
mkdir -p "$workspace"

git_commit() {
  git -C "$workspace" add -A
  git -C "$workspace" -c user.email="d1@classroom.invalid" -c user.name="D1 Classroom" commit -q -m "$1"
}

git -C "$workspace" init -q
rsync -a --exclude '.git/' --exclude '__pycache__/' --exclude '.pytest_cache/' "$baseline_root/stage-0/" "$workspace/"
git_commit "chore: start financing filter+export task (baseline + TASK/PROGRESS/DECISIONS scaffolding)"

rsync -a --exclude '.git/' --exclude '__pycache__/' --exclude '.pytest_cache/' "$baseline_root/stage-1/" "$workspace/"
git_commit "feat(financing): add customer_name filter; log decision D-001/D-002/D-003 and handoff state"

git -C "$workspace" commit -q --allow-empty -m "chore: session ended — see PROGRESS.md for next step"

echo "reset d1-handoff (workspace at $(git -C "$workspace" rev-parse --short HEAD), $(git -C "$workspace" log --oneline | wc -l | tr -d ' ') commits)"
