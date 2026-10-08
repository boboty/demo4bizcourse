from copy import deepcopy
import json
import shutil

import pytest

from app.assets import DEFAULT_ROOT, AssetValidationError, load, validate_assets
from app.executor import execute_cases
from app.migration import build_migration


def test_incremental_actions_and_statistics_are_consistent():
    result = build_migration()
    summary = result['summary']
    actions = {a['case_id']: a for a in result['case_actions']}
    assert len(result['rule_diff']) == 3
    assert actions['H-F01']['action'] == 'obsolete'
    for cid in ['H-F05', 'H-V10-04']:
        assert actions[cid]['action'] == 'modify'
        assert actions[cid]['before']['expected']['outcome'] == 'reject'
        assert actions[cid]['after']['expected']['outcome'] == 'accept'
    old_money = [c for c in load('history/v1_0_validated_baseline.json')['cases'] if c['kind'] == 'money']
    for before in old_money:
        after = actions[before['case_id']]['after']
        assert after['expected'] == before['expected']
        assert 'R-PROMO-RECALC' in after['rule_ids']
        assert 'P41' in after['source_ids']
    assert summary['history_total'] == summary['retain'] + summary['modify'] + summary['obsolete'] == 32
    assert summary['target_total'] == summary['history_total'] - summary['obsolete'] + summary['add']
    assert summary['behavior_affected'] < summary['affected_dependency_count']
    assert summary['provenance_only_count'] == len(old_money)


def test_regression_has_real_execution_and_coverage_protection():
    result = build_migration()
    regression = result['regression']
    assert len(regression['selected_ids']) == len(set(regression['selected_ids'])) <= 25
    assert 'H-F01' not in regression['selected_ids']
    assert 'H-M01' in regression['selected_ids']
    assert 'H-V10-06' in regression['selected_ids']
    assert regression['report']['failed'] == 0
    assert regression['report']['passed'] == len(regression['selected_ids'])
    assert execute_cases(result['target_cases'], '1.1')['failed'] == 0
    assert result['not_added'][0]['case_id'] == 'H-F12'
    for row in result['case_actions']:
        if row['action'] in ('add', 'modify'):
            assert row['case_id'] in regression['selected_ids']


def test_asset_validator_rejects_bad_historical_finance_expectation(tmp_path):
    root = tmp_path / 'assets'
    shutil.copytree(DEFAULT_ROOT, root)
    path = root / 'history/v1_0_validated_baseline.json'
    data = json.loads(path.read_text())
    next(c for c in data['cases'] if c['case_id'] == 'H-M01')['expected']['refund'] = '85.13'
    path.write_text(json.dumps(data))
    with pytest.raises(AssetValidationError, match='history execution'):
        validate_assets(root)
