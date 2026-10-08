"""只读自检：资产、真实测试、临时HTTP服务与全部课堂入口。"""
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.assets import validate_assets
from app.migration import build_migration
from app.state import ResetState


def main():
    process = None
    try:
        assets = validate_assets()
        print('[PASS] 必需材料、来源/版本/ID引用、20条假设用例与可信历史：', assets)
        migration = build_migration()
        assert migration['regression']['report']['failed'] == 0
        print('[PASS] 三项Rule Diff、增量动作与实际25条回归：', migration['summary'])
        ResetState().read()
        for name in ('index.html', 'app.js', 'style.css'):
            assert (ROOT / 'app/static' / name).is_file(), '缺少页面材料：' + name
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            port = probe.getsockname()[1]
        base = 'http://127.0.0.1:%s' % port
        process = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', str(port)],
                                   cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.monotonic() + 10
        while True:
            try:
                with urlopen(base + '/health', timeout=1) as response:
                    assert json.load(response)['status'] == 'OK'
                break
            except OSError:
                if process.poll() is not None or time.monotonic() >= deadline:
                    raise RuntimeError('本地服务未能启动；请检查Python依赖和端口环境')
                time.sleep(.1)
        for route in ['/', '/static/app.js', '/static/style.css'] + ['/api/lesson/%s' % n for n in range(2, 7)] + ['/api/practice/3', '/api/practice/6']:
            with urlopen(base + route, timeout=5) as response:
                assert response.status == 200 and response.read(), route
        with urlopen(Request(base + '/api/run-tests', method='POST', data=b''), timeout=5) as response:
            report = json.load(response)
            assert (report['total'], report['passed'], report['failed']) == (20, 20, 0)
        print('[PASS] 真实HTTP启动、页面本地资源、Demo 2～6、学员输入导出、20/20执行')
        print('DEMO READY — 无网络、无LLM API也可完整演示')
        return 0
    except Exception as exc:
        print('DEMO NOT READY — %s' % exc)
        return 1
    finally:
        if process is not None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == '__main__':
    raise SystemExit(main())
