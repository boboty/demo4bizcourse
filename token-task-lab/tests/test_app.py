from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_scenario_contract():
    body = client.get('/api/scenarios').json()
    assert 'tianjin-freight' in body
    assert body['tianjin-freight']['human_gates']


def test_run_never_fakes_token_numbers_in_skeleton():
    r = client.post('/api/runs', json={'scenario': 'tianjin-freight', 'mode': 'C', 'request_text': '天津新港到釜山，两个20GP，帮我看看船期和价格。'})
    assert r.status_code == 200
    body = r.json()
    assert body['evidence_level'] == 'skeleton_only'
    assert body['usage']['input_tokens'] is None
    assert body['usage']['output_tokens'] is None
    assert body['run_id']


def test_invalid_mode_is_rejected():
    r = client.post('/api/runs', json={'scenario': 'tianjin-freight', 'mode': 'X', 'request_text': 'test'})
    assert r.status_code == 400
