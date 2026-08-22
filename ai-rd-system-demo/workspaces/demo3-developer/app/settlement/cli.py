from __future__ import annotations
import json, sys
from pathlib import Path
from app.settlement.service import evaluate_candidate


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: ../../.venv/bin/python -m app.settlement.cli <cases.json>")
        return 2
    cases = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    out = [{"id": c["id"], **evaluate_candidate(c)} for c in cases]
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
