"""稳定交付指纹：相对 baseline 的全部文件内容（含非忽略 untracked），不依赖索引状态。"""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

DEFAULT_BASELINE = "a8804fa4dade32fd59fc9720441a58365a24fa85"
ROOT = Path(__file__).resolve().parents[2]


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def fingerprint(baseline=DEFAULT_BASELINE):
    tracked = git("diff", "--name-only", "-z", baseline).split(b"\0")
    untracked = git("ls-files", "--others", "--exclude-standard", "-z").split(b"\0")
    digest = hashlib.sha256()
    entries = []
    for raw in sorted(set(tracked + untracked) - {b""}):
        path = ROOT / raw.decode()
        data = path.read_bytes() if path.exists() else b""
        mode = b"file" if path.exists() else b"deleted"
        executable = b"x" if path.exists() and path.stat().st_mode & 0o111 else b"-"
        # 有长度前缀，避免名称、内容和删除状态之间的拼接歧义。
        for part in (raw, mode, executable, data):
            digest.update(len(part).to_bytes(8, "big"))
            digest.update(part)
        entries.append(raw.decode())
    return {"baseline": baseline, "fingerprint": digest.hexdigest(), "files": entries}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="计算相对 Git 基线的交付指纹（含未跟踪文件）")
    parser.add_argument("--baseline", default=DEFAULT_BASELINE)
    print(json.dumps(fingerprint(parser.parse_args().baseline), ensure_ascii=False, indent=2))
