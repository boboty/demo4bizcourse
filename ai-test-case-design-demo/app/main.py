"""本地课堂服务；所有数据与计算来自本目录的离线资产。"""
from decimal import Decimal
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from app.assets import load, project_demo2
from app.engine import calculate_finance_refund, calculate_proportional_refund, execute_v1_0_cases
from app.migration import build_migration
from app.selection import select_scenarios
from app.state import ResetState


BASE = Path(__file__).resolve().parent


def run_tests():
    fixture = load('cases/v1_0_executable.json')
    report = execute_v1_0_cases(fixture)
    titles = {c['case_id']: c['title'] for c in fixture['cases']}
    for row in report['cases']:
        row['title'] = titles[row['case_id']]
    report['scope'] = '按比例分摊假设执行的20条金额样例；预期依据尚待业务验证。'
    return report


def lesson_data(number, budget=15, manual=False):
    if number == 2:
        return project_demo2()
    if number == 3:
        data = select_scenarios(budget, manual)
        candidates = load('scenarios/candidates.json')
        data.update(all_scenarios=load('scenarios/candidates_v1_0.json')['scenarios'],
                    dimensions=candidates['dimensions'], theoretical_product=candidates['theoretical_product'])
        return data
    if number == 4:
        fixture = load('cases/v1_0_executable.json')
        order = fixture['cases'][0]['input']
        assumed = calculate_proportional_refund(order)['refund']
        correct = calculate_finance_refund(order, return_skus=order['return_skus'])
        gross = sum(Decimal(item['gross']) for item in order['items'])
        returning = sum(Decimal(item['gross']) for item in order['items'] if item['sku'] in order['return_skus'])
        return {'cases': fixture, 'order': order, 'finance': load('finance/after_sales_funds.json'),
                'comparison': {'assumed_refund': assumed, 'correct_refund': correct['refund'],
                               'difference': str(Decimal(assumed) - Decimal(correct['refund'])),
                               'remaining_gross': correct['remaining_gross'], 'remaining_discount': correct['remaining_discount'],
                               'discount_share': str(returning - Decimal(assumed)), 'gross_total': str(gross),
                               'paid': order['paid'], 'original_discount': order['original_discount']}}
    if number == 5:
        return {'round1': load('frozen/demo5_review_round1.json'), 'round2': load('frozen/demo5_review_round2.json'),
                'execution_report': run_tests(), 'finance': load('finance/after_sales_funds.json')}
    if number == 6:
        return dict(build_migration(), prd_v1_0=load('prd/prd_v1_0.json'), prd_v1_1=load('prd/prd_v1_1.json'))
    raise ValueError('课堂只包含Demo 2～6')


def create_app(state_dir=None):
    service = FastAPI(title='悦选商城 · AI测试用例课堂', docs_url=None, redoc_url=None)
    state = ResetState(state_dir)
    service.mount('/static', StaticFiles(directory=BASE / 'static', check_dir=False), name='static')

    @service.get('/')
    def index():
        return FileResponse(BASE / 'static/index.html')

    @service.get('/favicon.ico')
    def favicon():
        return Response(status_code=204)

    @service.get('/health')
    def health():
        return {'status': 'OK', 'mode': 'offline_deterministic'}

    @service.get('/api/state')
    def session_state():
        return JSONResponse(state.read(), headers={'Cache-Control': 'no-store'})

    @service.post('/api/reset')
    def reset():
        return state.reset()

    @service.post('/api/run-tests')
    def execute():
        return run_tests()

    @service.get('/api/lesson/{number}')
    def lesson(number: int, budget: int = 15, manual: bool = False):
        if number not in range(2, 7):
            raise HTTPException(404, '课堂只包含Demo 2～6')
        try:
            return lesson_data(number, budget, manual)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @service.get('/api/practice/{number}')
    def practice(number: int):
        tasks = {3: 'practice/student/demo3_scenario_design.json', 6: 'practice/student/demo6_incremental_update.json'}
        if number not in tasks:
            raise HTTPException(404, '学员实践仅提供第二讲与第四讲输入')
        task = load(tasks[number])
        return JSONResponse({'task': task, 'materials': {name: load(name) for name in task['input_files']}},
                            headers={'Content-Disposition': 'attachment; filename="demo%d-student-input.json"' % number})

    return service


app = create_app()
