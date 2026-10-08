"""确定性的场景预算裁剪、人工补漏和规则覆盖反查。"""
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.assets import load

SUPPORTED_BUDGETS = (10, 15, 20)
MANUAL_SCENARIO_ID = "SC36"
PROTECTED_SCENARIO_IDS = ("SC01", "SC19")
EQUIVALENCE_GROUPS = {
    "invalid_quantity": {
        "representative": "SC04",
        "members": ["SC04", "SC05"],
        "reason": "按相同的无效退货数量校验风险等价类抽样；不代表两种输入完全相同。",
    }
}


def select_scenarios(budget: int = 15, manual: bool = False,
                     root: Optional[Path] = None) -> Dict[str, Any]:
    """按风险分裁剪 V1.0 场景，并逐条规则反查场景引用。"""
    if budget not in SUPPORTED_BUDGETS:
        raise ValueError("budget must be one of %s" % (SUPPORTED_BUDGETS,))
    scenarios = load("scenarios/candidates_v1_0.json", root)["scenarios"]
    rules = load("business/rules_v1_0.json", root)["rules"]
    by_id = {row["scenario_id"]: row for row in scenarios}

    merged_ids = set()
    merge_records = []
    for group_id, group in EQUIVALENCE_GROUPS.items():
        representative = group["representative"]
        members = group["members"]
        if all(member in by_id for member in members):
            merged_ids.update(member for member in members if member != representative)
            merge_records.append({
                "equivalence_class": group_id,
                "representative_id": representative,
                "merged_ids": [member for member in members if member != representative],
                "reason": group["reason"],
            })

    def scored(scene: Dict[str, Any]) -> Dict[str, Any]:
        result = dict(scene)
        risk = scene["risk"]
        result["risk_score"] = risk["impact"] * risk["probability"] * risk["hard_to_detect"]
        result["cost"] = scene["execution_cost"]
        return result

    pool = [scored(scene) for scene in scenarios
            if scene["scenario_id"] not in merged_ids
            and scene["scenario_id"] not in PROTECTED_SCENARIO_IDS
            and scene["scenario_id"] != MANUAL_SCENARIO_ID]
    pool.sort(key=lambda scene: (-scene["risk_score"], scene["scenario_id"]))
    protected = [scored(by_id[sid]) for sid in PROTECTED_SCENARIO_IDS]
    automatic = protected + pool[:budget - len(protected)]
    chosen = list(automatic)
    manual_addition = None
    if manual:
        manual_scene = scored(by_id[MANUAL_SCENARIO_ID])
        replace_index = next((index for index in range(len(chosen) - 1, -1, -1)
                              if chosen[index]["scenario_id"] not in PROTECTED_SCENARIO_IDS), None)
        replaced = chosen[replace_index] if replace_index is not None else None
        if replaced:
            chosen[replace_index] = manual_scene
        else:
            chosen.append(manual_scene)
        manual_addition = {
            "scenario_id": MANUAL_SCENARIO_ID,
            "reason": "人工多维补漏：金卡、混合支付、优惠失效和渠道超时组合；各维度仍待确认。",
            "replaced_id": replaced["scenario_id"] if replaced else None,
            "replaced_reason": (
                "为保持预算上限，替换自动排序中的末位场景；其风险分为 %s，排序靠后。"
                % replaced["risk_score"] if replaced else None
            ),
        }
    selected_ids = [scene["scenario_id"] for scene in chosen]
    selected_set = set(selected_ids)
    automatic_ids = [scene["scenario_id"] for scene in automatic]
    automatic_set = set(automatic_ids)
    for scene in chosen:
        scene["selection_reason"] = (
            manual_addition["reason"] if scene["scenario_id"] == MANUAL_SCENARIO_ID
            else "课堂保护场景：固定保留正常申请和正常质检基线。"
                 if scene["scenario_id"] in PROTECTED_SCENARIO_IDS
            else "自动选择：风险分 %s，成本 %s；按风险分降序确定预算名额。"
                 % (scene["risk_score"], scene["cost"])
        )
    excluded = []
    for scene in scenarios:
        sid = scene["scenario_id"]
        if sid in selected_set:
            continue
        row = scored(scene)
        if sid in merged_ids:
            row["selection_reason"] = "由 SC04 代表参加排序；代表也可能因预算未入选。"
        elif sid == MANUAL_SCENARIO_ID:
            row["selection_reason"] = "预留人工多维补漏候选；仅 manual=True 时纳入。"
        elif sid in automatic_set and manual:
            row["selection_reason"] = "自动入选后被人工补漏场景替换，以保持预算上限。"
        else:
            row["selection_reason"] = "预算名额有限；风险排序未进入前 %s。" % budget
        excluded.append(row)

    def build_coverage(ids: List[str]) -> List[Dict[str, Any]]:
        result = []
        for rule in rules:
            covering = [sid for sid in ids if rule["rule_id"] in by_id[sid].get("rule_ids", [])]
            result.append({
                "rule_id": rule["rule_id"], "statement": rule["statement"],
                "source_ids": list(rule.get("source_ids", [])),
                "evidence_status": rule["evidence_status"],
                "covered_by": covering, "uncovered": not bool(covering),
            })
        return result

    pre_manual_coverage = build_coverage(automatic_ids)
    coverage = build_coverage(selected_ids)
    return {
        "version": "1.0", "budget": budget,
        "candidate_count": len(scenarios),
        "merged_candidate_count": len(scenarios) - len(merged_ids),
        "merge_groups": merge_records,
        "protected_ids": list(PROTECTED_SCENARIO_IDS),
        "initial_selected_ids": automatic_ids,
        "selected_ids": selected_ids,
        "selected_count": len(selected_ids),
        "scenarios": chosen,
        "excluded_scenarios": excluded,
        "manual_addition": manual_addition,
        "selection_policy": "课堂保护 SC01/SC19；剩余名额按 risk_score=impact×probability×hard_to_detect 降序裁剪，cost 单列；SC36 仅人工补漏时纳入。",
        "pre_manual_uncovered": [row["rule_id"] for row in pre_manual_coverage if row["uncovered"]],
        "post_uncovered": [row["rule_id"] for row in coverage if row["uncovered"]],
        "coverage": coverage,
        "coverage_matrix": {entry["rule_id"]: list(entry["covered_by"])
                             for entry in coverage},
        "coverage_note": "coverage 表示场景引用了规则，不代表规则已确认；缺失、推断与冲突证据等级均保留。",
    }
