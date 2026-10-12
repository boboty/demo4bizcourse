"""从学生输入资产导出两套独立的学员材料包（Demo 3 / Demo 6），严格排除 practice/instructor/。"""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.student_export import ExportError, export_all

DEFAULT_OUT = ROOT / 'exports' / 'student-packages'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT, help='输出目录（默认 exports/student-packages）')
    args = parser.parse_args()
    try:
        written = export_all(args.out)
    except (ExportError, OSError, ValueError) as exc:
        print('EXPORT NOT READY — %s' % exc)
        raise SystemExit(1)
    for slug, files in written.items():
        print('[OK] %s' % slug)
        for path in files:
            print('     %s  (%d KB)' % (path.relative_to(args.out.parent.parent) if args.out.is_relative_to(ROOT) else path,
                                       max(1, path.stat().st_size // 1024)))
    print('STUDENT PACKAGES READY — 两套材料包彼此独立（各含文件夹与 ZIP），已通过讲师答案泄漏扫描。输出：%s' % args.out)


if __name__ == '__main__':
    main()
