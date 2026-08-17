"""将课堂演示恢复为尚未产生运行证据的初始状态。"""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = PROJECT_ROOT / "evidence"
GENERATED_FILES = (
    "generated-test-report.md",
    "independent-review-report.md",
    "final-test-report.md",
)


def reset_demo() -> None:
    EVIDENCE_DIR.mkdir(exist_ok=True)
    removed = 0
    for filename in GENERATED_FILES:
        report = EVIDENCE_DIR / filename
        if report.exists():
            report.unlink()
            removed += 1
    print(f"Demo reset complete: cleared {removed} generated evidence file(s).")
    print("Source requirements and both test versions are unchanged.")


if __name__ == "__main__":
    reset_demo()

