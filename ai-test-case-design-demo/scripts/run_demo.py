"""页面异常时使用的确定性命令行兜底，不伪装成实时AI。"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.main import lesson_data, run_tests

parser = argparse.ArgumentParser()
parser.add_argument('--demo', type=int, choices=range(2, 7), required=True)
parser.add_argument('--budget', type=int, choices=(10, 15, 20), default=15)
parser.add_argument('--manual', action='store_true')
parser.add_argument('--reveal', action='store_true', help='Demo4执行后揭示财务规则')
args = parser.parse_args()
data = lesson_data(args.demo, args.budget, args.manual)
if args.demo == 4:
    output = {'execution': run_tests()}
    if args.reveal:
        output.update(finance=data['finance'], comparison=data['comparison'])
elif args.demo == 6:
    output = {key: data[key] for key in ('summary', 'rule_diff', 'case_actions', 'regression', 'comparison')}
else:
    output = data
print(json.dumps(output, ensure_ascii=False, indent=2))
