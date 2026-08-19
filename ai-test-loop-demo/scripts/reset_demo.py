"""Reset 课堂现场：只清理课堂 Agent 在 agent_workspace/ 中生成的测试、报告与证据。

不会修改：docs/business-rules.md、app/ 被测代码、tests/ 项目自带 smoke 测试。
可重复执行（幂等）。
"""

import shutil
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = PROJECT_ROOT / "agent_workspace"
PRESERVE = {"README.md", ".gitkeep", ".DS_Store"}


def reset_demo() -> None:
    WORKSPACE.mkdir(exist_ok=True)
    removed: list[str] = []
    for child in sorted(WORKSPACE.iterdir()):
        if child.name in PRESERVE:
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
        removed.append(str(child.relative_to(PROJECT_ROOT)))
    if removed:
        print("Removed classroom-generated artifacts:")
        for path in removed:
            print(f"  - {path}")
    else:
        print("agent_workspace/ is already clean.")
    print("Demo reset complete: business rules and app code are untouched.")


if __name__ == "__main__":
    reset_demo()
