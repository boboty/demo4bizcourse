"""恢复课堂显示基线；运行中的页面在3秒内通过本地复位序号同步。"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.assets import validate_assets
from app.state import ResetState

if __name__ == '__main__':
    try:
        ResetState().reset()
        validate_assets()
        print('DEMO RESET — Demo2/阶段1，预算15，未补漏，执行与财务揭示均清空。')
        print('已打开页面3秒内自动复位；离线或休眠页面请刷新。稳定业务资产不会被改写。')
    except Exception as exc:
        print('RESET NOT READY — %s' % exc)
        raise SystemExit(1)
