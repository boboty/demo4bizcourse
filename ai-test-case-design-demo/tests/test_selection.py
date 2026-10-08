import pytest

from app.selection import select_scenarios


@pytest.mark.parametrize("budget", [10, 15, 20])
def test_budget_limit_and_deterministic_selection(budget):
    first = select_scenarios(budget)
    second = select_scenarios(budget)
    assert len(first["selected_ids"]) <= budget
    assert first["selected_ids"] == second["selected_ids"]
    assert first["initial_selected_ids"] == first["selected_ids"]
    assert {"SC01", "SC19"} <= set(first["selected_ids"])
    assert first["selected_count"] == len(first["selected_ids"])
    assert first["candidate_count"] == 41
    assert first["merged_candidate_count"] == 40


def test_manual_addition_replaces_last_auto_choice_and_includes_sc36():
    result = select_scenarios(15, manual=True)
    assert "SC36" in result["selected_ids"]
    assert len(result["selected_ids"]) == 15
    assert "SC36" not in result["initial_selected_ids"]
    detail = result["manual_addition"]
    expected_replaced = next(sid for sid in reversed(result["initial_selected_ids"])
                             if sid not in result["protected_ids"])
    assert detail["replaced_id"] == expected_replaced
    assert detail["replaced_id"] not in result["selected_ids"]
    assert detail["reason"] and detail["replaced_reason"]
    assert {"SC01", "SC19"} <= set(result["selected_ids"])
    assert len(result["selected_ids"]) <= 15
    assert result["pre_manual_uncovered"] != []


def test_coverage_matches_rule_references_and_preserves_evidence():
    result = select_scenarios(20)
    selected = {scene["scenario_id"]: scene for scene in result["scenarios"]}
    for row in result["coverage"]:
        actual = [sid for sid, scene in selected.items()
                  if row["rule_id"] in scene["rule_ids"]]
        assert row["covered_by"] == actual
        assert result["coverage_matrix"][row["rule_id"]] == actual
        assert row["uncovered"] is (not actual)
        assert row["evidence_status"] in {"fact", "inference", "missing", "conflict"}
    assert {row["evidence_status"] for row in result["coverage"]} >= {"missing", "inference"}
    assert "不代表规则已确认" in result["coverage_note"]


def test_equivalence_group_is_explicit():
    result = select_scenarios(20)
    assert result["merge_groups"] == [{
        "equivalence_class": "invalid_quantity",
        "representative_id": "SC04",
        "merged_ids": ["SC05"],
        "reason": "按相同的无效退货数量校验风险等价类抽样；不代表两种输入完全相同。",
    }]
    assert any(row["scenario_id"] == "SC05" for row in result["excluded_scenarios"])


@pytest.mark.parametrize("budget", [0, 11, 30, "15"])
def test_unsupported_budget_is_rejected(budget):
    with pytest.raises(ValueError):
        select_scenarios(budget)
