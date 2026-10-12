"""只读自检：资产、真实测试、临时HTTP服务与全部课堂入口。"""
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import ailab
from app.assets import validate_assets
from app.migration import build_migration
from app.student_export import export_all
from app.state import ResetState


def main():
    process = None
    try:
        assets = validate_assets()
        print('[PASS] 必需材料、来源/版本/ID引用、20条假设用例与可信历史：', assets)
        migration = build_migration()
        assert migration['regression']['report']['failed'] == 0
        print('[PASS] 三项Rule Diff、增量动作与实际25条回归：', migration['summary'])
        for kind in ailab.PROMPT_KINDS:
            built = ailab.build_prompt(kind, 15)
            assert built['prompt'] and 'demo_assets' not in built['prompt'], kind
        assert '49.00' not in ailab.build_prompt('d4_eval1')['prompt'] + ailab.build_prompt('d4_eval2')['prompt']
        assert 'F10' not in ailab.build_prompt('d5_review1')['prompt']
        second = ailab.build_d5_prompt(2)
        assert second['prompt'].replace(second['finance_block'], '') == ailab.build_prompt('d5_review1')['prompt']
        print('[PASS] AI实验提示词：6类提示词自带数据；财务规范揭示前不含49.00；Demo 5两轮仅差独立财务规范')
        with tempfile.TemporaryDirectory() as folder:
            written = export_all(Path(folder))
            assert sorted(written) == ['demo3-scenario-selection', 'demo6-incremental-update'], written
        print('[PASS] 两套学员材料包可导出（HTML+TXT），且已通过讲师答案泄漏扫描')
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
        with urlopen(base + '/api/lesson/4', timeout=5) as response:
            assert '49.00' not in response.read().decode('utf-8'), '财务规范揭示前接口不得返回正确金额'
        for kind in ailab.PROMPT_KINDS:
            request = Request(base + '/api/ai-lab/prompt', method='POST', data=json.dumps({'kind': kind, 'budget': 10}).encode(),
                              headers={'Content-Type': 'application/json'})
            with urlopen(request, timeout=5) as response:
                assert json.load(response)['prompt'], kind
        with urlopen(Request(base + '/api/run-tests', method='POST', data=b''), timeout=5) as response:
            report = json.load(response)
            assert (report['total'], report['passed'], report['failed']) == (20, 20, 0)
        print('[PASS] 真实HTTP启动、页面本地资源、Demo 2～6、学员输入导出、AI实验提示词接口、20/20执行')
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
