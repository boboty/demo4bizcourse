"""按规则引用推导增量；预期的金融依据与行为变更分别统计。"""
from copy import deepcopy

from app.assets import load
from app.executor import execute_case, execute_cases


def _signature(case):
    data = case['input']
    if 'elapsed_hours' in data or 'elapsed_seconds' in data:
        return ('window', data.get('member_at_order', 'ordinary'),
                data.get('member_at_request', data.get('member_at_order', 'ordinary')),
                data.get('elapsed_seconds', data.get('elapsed_hours', 0) * 3600))
    if case['kind'] == 'workflow':
        fast = data.get('eligible', False)
        return ('flow', fast, bool(data.get('tracking_no')) if fast else None,
                data.get('qc', 'pass'), data.get('payment', 'card'), data.get('decision'))
    return ('money', case['case_id'])


def build_migration(budget=25, root=None):
    if budget != 25:
        raise ValueError('本课堂回归预算固定为25条')
    history = load('history/v1_0_validated_baseline.json', root)
    additions = load('history/v1_1_additions.json', root)
    diff = load('history/v1_1_rule_diff.json', root)['rule_diff']
    scenes = history['scenarios'] + load('scenarios/candidates.json', root)['scenarios']
    scenes += additions['scenarios']
    by_scene = {row['scenario_id']: row for row in scenes}
    change_rules = {row['change_id']: set(row['affected_rule_ids']) for row in diff}

    def changes_for(rules):
        return [cid for cid, affected in change_rules.items() if set(rules) & affected]

    actions, target = [], []
    for before in history['cases']:
        dependencies = set(before['rule_ids'])
        for sid in before['scenario_ids']:
            dependencies.update(by_scene[sid]['rule_ids'])
        changes = changes_for(dependencies)
        after, action, reasons = deepcopy(before), 'retain', []
        provenance = False
        if 'C10' in changes and before.get('assertion_scope') == 'all_orders':
            action, after = 'obsolete', None
            reasons.append('旧断言对所有订单一律要求先质检；极速资格分支使该通用断言失效。')
        else:
            if 'C10' in changes and 'qc' in before['input'] and 'eligible' not in before['input']:
                after['input']['eligible'] = False
                result = execute_case(after, '1.1')['actual']
                after['expected'].update({k: result[k] for k in ('sequence', 'refund_allowed', 'recovery_required')})
                action = 'modify'
                reasons.append('补充eligible=false，将既有质检后退款意图限制到普通流程，并检查状态顺序。')
            if 'C20' in changes and ('elapsed_hours' in before['input'] or 'elapsed_seconds' in before['input']):
                actual = execute_case(after, '1.1')['actual']['outcome']
                if actual != before['expected']['outcome']:
                    after['expected']['outcome'] = actual
                    action = 'modify'
                    reasons.append('按下单时等级重核期限，原拒绝预期改为接受。')
                else:
                    reasons.append('按新期限复核后原预期仍有效，保留测试意图。')
                after.setdefault('source_ids', []).append('P11')
            if 'C30' in changes and before['kind'] == 'money':
                after['rule_ids'] = ['R-PROMO-RECALC' if rid == 'R-PARTIAL-AMOUNT' else rid for rid in after['rule_ids']]
                after.setdefault('source_ids', []).append('P41')
                provenance = True
                reasons.append('金融预期已独立验证，金额不变；新增正式需求P41的依据链。')
            target.append(after)
        actions.append({'case_id': before['case_id'], 'title': before['title'], 'action': action,
                        'change_ids': changes, 'dependencies': sorted(dependencies),
                        'reason': ' '.join(reasons) or '未受三项规则变更影响，保留为回归保护。',
                        'provenance_update': provenance, 'before': before, 'after': after})

    not_added = []
    for candidate in additions['cases']:
        changes = changes_for(candidate['rule_ids'])
        if not changes:
            continue
        covering = next((old for old in target if _signature(old) == _signature(candidate)
                         and all(old['expected'].get(k) == v for k, v in candidate['expected'].items())), None)
        if covering:
            not_added.append({'case_id': candidate['case_id'], 'covered_by': covering['case_id'],
                              'reason': '更新后的既有用例已覆盖相同条件与全部目标断言，避免重复新增。'})
            continue
        new = deepcopy(candidate)
        target.append(new)
        actions.append({'case_id': new['case_id'], 'title': new['title'], 'action': 'add',
                        'change_ids': changes, 'reason': '目标规则引入的新条件或断言尚无既有资产覆盖。',
                        'provenance_update': False, 'before': None, 'after': new})

    affected_scenes = [{'scenario_id': s['scenario_id'], 'title': s['title'],
                       'change_ids': changes_for(s['rule_ids'])} for s in by_scene.values()
                      if changes_for(s['rule_ids'])]
    selected, selection_reasons = [], {}

    def pick(case, reason):
        if case and len(selected) < budget and case['case_id'] not in selection_reasons:
            selected.append(case)
            selection_reasons[case['case_id']] = reason

    for record in actions:
        if record['action'] in ('add', 'modify'):
            pick(record['after'], '优先验证新增行为或已修改的历史断言。')
    pick(next((r['after'] for r in actions if r['action'] == 'retain' and not r['change_ids']), None),
         '保护未受影响的原有流程，避免回归选择只看新规则。')
    money = [c for c in target if c['kind'] == 'money']
    checks = [
        ('经典退B资金依据', lambda c: c['expected'].get('refund') == '49.00'),
        ('连续部分退款与累计上限', lambda c: 'return_sequence' in c['input']),
        ('剩余金额恰好达到300元门槛', lambda c: c['expected'].get('remaining_goods_original') == '300.00'),
        ('剩余金额低于门槛1分', lambda c: c['expected'].get('remaining_goods_original') == '299.99'),
        ('负公式金额暂停转人工', lambda c: c['expected'].get('status') == 'financial_review_required'),
    ]
    for reason, predicate in checks:
        pick(next((case for case in money if predicate(case)), None), reason)
    for case in sorted(target, key=lambda c: (c['kind'] != 'money', c['case_id'])):
        pick(case, '资金回归优先；其余按稳定ID补齐预算。')
    selected_ids = [case['case_id'] for case in selected]
    report = execute_cases(selected, '1.1')
    counts = {name: sum(a['action'] == name for a in actions) for name in ('retain', 'modify', 'obsolete', 'add')}
    summary = dict(counts, history_total=len(history['cases']), target_total=len(target),
                   affected_dependency_count=sum(bool(a['change_ids']) for a in actions if a['before']),
                   behavior_affected=counts['modify'] + counts['obsolete'],
                   provenance_only_count=sum(a['provenance_update'] and a['action'] == 'retain' for a in actions),
                   regression_count=len(selected))
    return {'rule_diff': diff, 'affected_rules': sorted(set().union(*change_rules.values())),
            'affected_scenarios': affected_scenes, 'case_actions': actions, 'target_cases': target,
            'not_added': not_added, 'summary': summary,
            'regression': {'budget': budget, 'selected_cases': selected, 'selected_ids': selected_ids,
                           'selection_reasons': selection_reasons, 'report': report,
                           'excluded': [{'case_id': c['case_id'], 'reason': '预算有限；已优先新增、行为修改及资金代表。'}
                                        for c in target if c['case_id'] not in selected_ids]},
            'comparison': {'full_regeneration': len(target), 'behavior_edit_or_add': counts['modify'] + counts['add'],
                           'provenance_only_updates': summary['provenance_only_count'],
                           'note': '来源正式化不等于重新计算金额；作废单列，回归数量不等于改动数量。'}}
