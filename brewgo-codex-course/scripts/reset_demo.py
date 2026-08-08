#!/usr/bin/env python3
"""Restore the editable BrewGo classroom baseline and empty generated outputs."""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = ROOT / "data" / "expected"
WORK = ROOT / "data" / "work"
OUTPUTS = ROOT / "outputs"


def main() -> None:
    if not EXPECTED.is_dir():
        raise SystemExit("Missing data/expected. Re-sync the BrewGo classroom snapshot before resetting.")
    if WORK.exists():
        shutil.rmtree(WORK)
    shutil.copytree(EXPECTED, WORK)
    OUTPUTS.mkdir(exist_ok=True)
    for item in OUTPUTS.iterdir():
        if item.name == ".gitkeep":
            continue
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()
    print("Reset complete: data/work restored from data/expected; outputs cleared; data/raw untouched.")


if __name__ == "__main__":
    main()
