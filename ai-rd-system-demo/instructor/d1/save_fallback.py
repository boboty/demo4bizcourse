#!/usr/bin/env python3
"""保存最近一次完整三级 live 证据，供课堂超时时展示。"""
from __future__ import annotations
import argparse, json, shutil
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--source", type=Path, required=True); parser.add_argument("--destination", type=Path, required=True); args = parser.parse_args()
    levels = ("level1", "level2", "level3")
    results = {level: json.loads((args.source / f"latest-{level}" / "result.json").read_text(encoding="utf-8")) for level in levels}
    if any(item.get("run_status") in {"TIMEOUT", "FAILED"} for item in results.values()): raise SystemExit("存在未完成的 live 阶段，不能保存 fallback")
    if results["level3"].get("phase") != "execute" or not results["level3"].get("self_check", {}).get("适用"): raise SystemExit("Level 3 尚未完成真实开发与开发侧自检，不能保存 fallback")
    args.destination.mkdir(parents=True, exist_ok=True)
    for level in levels:
        target = args.destination / level
        if target.exists() or target.is_symlink():
            if target.is_dir() and not target.is_symlink(): shutil.rmtree(target)
            else: target.unlink()
        shutil.copytree(args.source / f"latest-{level}", target)
    metadata = {"kind": "SAVED_EVIDENCE", "source": str(args.source), "run_ids": {level: results[level]["manifest"].get("run_id") for level in levels}, "note": "最近一次完整三级 instructor evidence snapshot，不是当前 live run。"}
    (args.destination / "snapshot.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"saved evidence snapshot: {args.destination}"); return 0


if __name__ == "__main__": raise SystemExit(main())
