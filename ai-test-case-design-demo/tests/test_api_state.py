import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.state import ResetState


def test_all_lesson_routes_and_local_execution(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        assert client.get('/health').json()['status'] == 'OK'
        for number in range(2, 7):
            assert client.get('/api/lesson/%s' % number).status_code == 200
        assert client.get('/api/lesson/3?budget=11').status_code == 422
        assert client.get('/api/lesson/1').status_code == 404
        report = client.post('/api/run-tests').json()
        assert (report['total'], report['passed'], report['failed']) == (20, 20, 0)
        assert client.get('/api/lesson/4').json()['comparison']['correct_refund'] == '49.00'


def test_reset_epoch_and_cli_state_share_baseline_signal(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        assert client.get('/api/state').json() == {'epoch': 0}
        assert client.post('/api/reset').json() == {'epoch': 1}
        assert ResetState(tmp_path).reset() == {'epoch': 2}
        assert client.get('/api/state').json() == {'epoch': 2}
        assert client.post('/api/run-tests').json()['passed'] == 20


def test_corrupted_reset_state_can_be_recovered(tmp_path):
    state = ResetState(tmp_path)
    state.path.write_text('not-json')
    assert state.reset() == {'epoch': 1}


def test_student_bundle_preserves_information_boundary(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        before = client.get('/api/practice/3').json()
        text = json.dumps(before, ensure_ascii=False)
        assert '49.00' not in text and '15日' not in text and 'R-FAST-REFUND' not in text
        assert 'reference' not in before['materials']
        later = client.get('/api/practice/6').json()
        assert 'history/v1_0_validated_baseline.json' in later['materials']
