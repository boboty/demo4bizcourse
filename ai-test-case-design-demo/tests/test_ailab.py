"""AI 实验：提示词的信息边界、独立可执行性，以及粘贴输出与本地确定性结果的对照。"""
import json
import re

import pytest
from fastapi.testclient import TestClient

from app import ailab
from app.assets import load
from app.main import create_app
from app.migration import build_migration
from app.selection import select_scenarios

ALL_KINDS = ["d3_select", "d4_eval1", "d4_eval2", "d5_review1", "d5_review2", "d6_impact"]


@pytest.fixture()
def client(tmp_path):
    with TestClient(create_app(tmp_path)) as c:
        yield c


@pytest.mark.parametrize("kind", ALL_KINDS)
def test_prompts_are_self_contained(kind):
    prompt = ailab.build_prompt(kind)["prompt"]
    for forbidden in ("demo_assets", ".json", "本页面", "附件", "上传", "Demo ", "课堂", "冻结", "确定性算法"):
        assert forbidden not in prompt, (kind, forbidden)
    assert "【输出格式】" in prompt and len(prompt) > 1500


# ───────────── Demo 3 ─────────────

def test_d3_prompt_changes_with_budget_and_contains_all_candidates():
    prompts = {b: ailab.build_prompt("d3_select", budget=b)["prompt"] for b in (10, 15, 20)}
    assert len(set(prompts.values())) == 3
    for budget, prompt in prompts.items():
        assert "不超过 %d 条" % budget in prompt and "FINAL_SELECTION" in prompt
        ids = set(re.findall(r"^(SC\d{2})｜", prompt, flags=re.M))
        assert len(ids) == 41 and "SC36" in ids
    with pytest.raises(ValueError):
        ailab.build_prompt("d3_select", budget=11)


def test_d3_prompt_does_not_leak_algorithm_answer():
    prompt = ailab.build_prompt("d3_select", budget=15)["prompt"]
    for forbidden in ("保护", "人工补漏", "替换", "selection_reason", "初始选择"):
        assert forbidden not in prompt


@pytest.mark.parametrize("budget", [10, 15, 20])
def test_d3_algorithm_budget_and_sc36_replacement(budget):
    result = ailab.analyze_d3(budget, True, "")
    assert result["algorithm"]["count"] == budget and result["final"]["count"] == budget
    assert "SC36" in result["final"]["ids"] and "SC36" not in result["algorithm"]["ids"]
    replaced = result["final"]["manual_addition"]["replaced_id"]
    assert replaced in result["algorithm"]["ids"] and replaced not in result["final"]["ids"]
    assert result["final"]["risk_total"] >= result["algorithm"]["risk_total"] - 1000  # 仅结构性检查


def test_d3_ai_equal_to_algorithm_has_no_difference():
    base = select_scenarios(15)["selected_ids"]
    result = ailab.analyze_d3(15, False, "FINAL_SELECTION: " + ", ".join(base))
    assert result["source"] == "FINAL_SELECTION" and result["parsed"]
    assert result["compare_baseline"]["ai_only"] == [] and result["compare_baseline"]["algorithm_only"] == []
    assert sorted(result["compare_baseline"]["common"]) == sorted(base)
    assert result["uncovered"]["ai"] == result["uncovered"]["baseline"]


def test_d3_ai_difference_overrun_and_illegal_ids():
    base = select_scenarios(10)["selected_ids"]
    legal = ["SC%02d" % n for n in range(1, 39)]
    padding = [i for i in legal if i not in base and i not in ("SC36", "SC26")][:4]
    ai = ["SC36", "SC26", "SC01", "SC99", "SC40", "SC36"] + [i for i in base if i not in ("SC01", "SC19")] + padding
    decoy = next(i for i in reversed(legal) if i not in ai)
    result = ailab.analyze_d3(10, False, "说明文字 %s\nFINAL_SELECTION: %s" % (decoy, ", ".join(ai)))
    assert result["ai"]["illegal_ids"] == ["SC99", "SC40"]
    assert result["ai"]["ids"].count("SC36") == 1
    assert result["ai"]["over_budget"] is True and any("超过预算" in n for n in result["notes"])
    assert "SC36" in result["compare_baseline"]["ai_only"]
    assert "SC19" in result["compare_baseline"]["algorithm_only"]
    assert decoy not in result["ai"]["ids"]  # 只认 FINAL_SELECTION，不收说明文字里的ID


def test_d3_fallback_and_unparseable_do_not_raise():
    fallback = ailab.analyze_d3(15, False, "我选 SC01、SC19 和 SC26")
    assert fallback["source"] == "fallback" and fallback["ai"]["ids"] == ["SC01", "SC19", "SC26"]
    assert any("FINAL_SELECTION" in n for n in fallback["notes"])
    empty = ailab.analyze_d3(15, False, "完全没有场景ID")
    assert empty["parsed"] is False and empty["ai"]["ids"] == [] and empty["notes"]
    assert ailab.analyze_d3(15, False, "")["parsed"] is False


def test_d3_coverage_matches_selection_engine_and_separates_evidence():
    result = ailab.analyze_d3(15, True, "FINAL_SELECTION: SC26, SC36, SC13")
    final = select_scenarios(15, True)
    for row in result["coverage"]:
        reference = next(r for r in final["coverage"] if r["rule_id"] == row["rule_id"])
        assert row["final"] == reference["covered_by"]
        assert row["evidence_status"] == reference["evidence_status"]
    assert result["uncovered"]["final"] == final["post_uncovered"]
    # 规则被场景引用 ≠ 规则已确认：存在被AI引用却仍为 missing 的规则
    assert any(r["ai"] and r["evidence_status"] == "missing" for r in result["coverage"])


def test_d3_budgets_produce_different_algorithm_results():
    ids = {b: tuple(ailab.analyze_d3(b, False, "")["algorithm"]["ids"]) for b in (10, 15, 20)}
    assert len(set(ids.values())) == 3


# ───────────── Demo 4 ─────────────

def test_d4_first_prompt_withholds_finance_answer():
    prompt = ailab.build_prompt("d4_eval1")["prompt"]
    for secret in ("49.00", "36.13", "F10", "F20", "YS-FIN", "独立财务规范", "财务规范"):
        assert secret not in prompt, secret
    assert "85.13" in prompt and "20 条，通过 20 条，失败 0 条" in prompt
    assert len(re.findall(r"^TC\d{2}｜PASS｜", prompt, flags=re.M)) == 20
    assert "P40" in prompt and "Q30" in prompt  # PRD 与待确认事项


def test_d4_second_prompt_adds_rules_but_not_answers():
    first, second = ailab.build_prompt("d4_eval1")["prompt"], ailab.build_prompt("d4_eval2")["prompt"]
    for rule in ("F10：", "F20：", "F30：", "F40：", "YS-FIN-AFTERSALES-01", "RECOMPUTE"):
        assert rule in second
    for secret in ("49.00", "36.13", "worked_example"):
        assert secret not in second
    assert "85.13" in second and len(second) > len(first)
    carried = ailab.build_prompt("d4_eval2", previous="上一轮结论：预期口径只是假设")["prompt"]
    assert "上一轮结论：预期口径只是假设" in carried and "你上一轮的评价" in carried


def test_d4_lesson_api_gates_finance_until_reveal(client):
    hidden = client.get("/api/lesson/4").json()
    assert set(hidden) == {"cases", "order"}
    text = json.dumps(hidden, ensure_ascii=False)
    assert "49.00" not in text and "36.13" not in text and "F10" not in text
    revealed = client.get("/api/lesson/4?reveal=true").json()
    assert revealed["comparison"]["correct_refund"] == "49.00"
    assert revealed["comparison"]["assumed_refund"] == "85.13" and revealed["comparison"]["difference"] == "36.13"
    report = client.post("/api/run-tests").json()
    assert (report["total"], report["passed"], report["failed"]) == (20, 20, 0)
    assert "49.00" not in json.dumps(report)


def test_d4_finance_reference_and_recompute_comparison():
    reference = ailab.finance_reference()
    assert reference["TC01"]["refund"] == "49.00" and reference["TC01"]["test_expected"] == "85.13"
    assert reference["TC14"]["status"] == "financial_review_required"
    perfect = "\n".join("%s=%s" % (tc, "REVIEW" if row["status"] != "refund_calculated" else row["refund"])
                        for tc, row in reference.items())
    out = ailab.analyze_d4(2, "发现...\nRECOMPUTE:\n%s\nEXPECTATIONS=CONTRADICTED\nCLASSIC_B_REFUND=49.00\n"
                              "EVIDENCE_USED=F10,F20\nCONCLUSION_REVISED=YES" % perfect)
    assert out["recompute_found"] == 20 and out["recompute_match"] == 20
    assert out["classic_b_correct"] is True and out["markers"]["expectations"] == "CONTRADICTED"
    assert out["wrong_expectations"] == sum(r["expectation_wrong"] for r in out["reference"]) > 10
    wrong = ailab.analyze_d4(2, "RECOMPUTE:\nTC01=85.13\nCLASSIC_B_REFUND=85.13")
    assert wrong["classic_b_correct"] is False and wrong["recompute_match"] == 0
    assert ailab.analyze_d4(2, "随便写点什么")["parsed"] is False


def test_d4_round1_analysis_never_reveals_correct_amount():
    out = ailab.analyze_d4(1, "EXPECTATIONS=UNSUPPORTED\nCLASSIC_B_REFUND=85.13\nEVIDENCE_USED=P40")
    assert out["vs_test_expected"] == "same" and "49.00" not in json.dumps(out)
    unknown = ailab.analyze_d4(1, "EXPECTATIONS=UNSUPPORTED\nCLASSIC_B_REFUND=UNKNOWN")
    assert "49.00" not in json.dumps(unknown) and unknown["markers"]["classic_b_amount"] is None


# ───────────── Demo 5 ─────────────

def test_d5_rounds_differ_only_by_independent_finance_spec():
    one, two = ailab.build_d5_prompt(1), ailab.build_d5_prompt(2)
    assert two["finance_block"] and "F20：" in two["finance_block"]
    assert two["prompt"].replace(two["finance_block"], "") == one["prompt"]
    assert "YS-FIN-AFTERSALES-01" not in one["prompt"] and "F10" not in one["prompt"]
    assert "49.00" not in one["prompt"] and "49.00" not in two["prompt"]
    assert "独立财务规范" in two["prompt"]


def test_d5_compare_reports_difference_and_handles_partial_input():
    both = ailab.analyze_d5("EXPECTATIONS=UNSUPPORTED\nCLASSIC_B_REFUND=UNKNOWN\nEVIDENCE_USED=P40",
                            "差额 36.13，应退 49.00\nEXPECTATIONS=CONTRADICTED\nCLASSIC_B_REFUND=49.00\nEVIDENCE_USED=F10,F20",
                            "模型甲", "模型乙")
    assert both["input_difference"]["identical_after_removing_block"] is True
    assert both["input_difference"]["round1_contains_finance"] is False and both["input_difference"]["round2_contains_finance"] is True
    assert both["round1"]["expectations"] == "UNSUPPORTED" and both["round2"]["mentions_49"] and both["round2"]["mentions_36_13"]
    assert any("不等于获得新的业务证据" in n for n in both["notes"])
    partial = ailab.analyze_d5("EXPECTATIONS=UNSUPPORTED", "")
    assert partial["notes"] and partial["round2"]["expectations"] is None


# ───────────── Demo 6 ─────────────

def test_d6_prompt_has_baseline_changes_and_withholds_results():
    prompt = ailab.build_prompt("d6_impact")["prompt"]
    history = load("history/v1_0_validated_baseline.json")
    for case in history["cases"]:
        assert case["case_id"] + "｜" in prompt
    for change in ("C10｜", "C20｜", "C30｜", "R-FAST-REFUND", "15日", "F10：", "P31", "P11", "P41"):
        assert change in prompt
    for secret in ("回归", "25/25", "保留 27", "新增 14", "R-QC、R-MEMBER", "R-FAST-REFUND、R-QC"):
        assert secret not in prompt


def test_d6_deterministic_assets_unchanged_by_lab():
    ailab.analyze_d6("anything")
    migration = build_migration()
    summary = migration["summary"]
    assert (summary["retain"], summary["modify"], summary["obsolete"], summary["add"]) == (27, 4, 1, 14)
    assert summary["history_total"] == 32 and summary["target_total"] == 45
    report = migration["regression"]["report"]
    assert (report["total"], report["passed"], report["failed"]) == (25, 25, 0)


def _perfect_d6_answer(retain_all=False, modify_money=False):
    migration = build_migration()
    rows = []
    for a in migration["case_actions"]:
        if not a["before"]:
            continue
        action = a["action"]
        if retain_all:
            action = "retain"
        elif modify_money and a["case_id"].startswith("H-M"):
            action = "modify"
        rows.append("| %s | %s | 理由 |" % (a["case_id"], {"retain": "保留", "modify": "修改", "obsolete": "作废"}[action]))
    news = ["| N%02d | 新增 | R-X |" % i for i in range(1, 15)]
    return "AFFECTED_RULES: %s\nAFFECTED_SCENARIOS: HS-F01, HS-F02\n%s\n%s\nNEW_CASE_COUNT=14" % (
        ", ".join(migration["affected_rules"]), "\n".join(rows), "\n".join(news))


def test_d6_matching_answer_agrees_with_deterministic_analysis():
    out = ailab.analyze_d6(_perfect_d6_answer())
    assert out["groups"]["agree"] and len(out["groups"]["agree"]) == 32
    assert out["groups"]["missed"] == [] and out["groups"]["over_reaction"] == []
    assert out["rules"]["ai_only"] == [] and out["rules"]["algorithm_only"] == []
    assert out["counts"]["ai_new"] == 14 == out["counts"]["algorithm_new"]


def test_d6_detects_missed_and_unnecessary_rebuild():
    missed = ailab.analyze_d6(_perfect_d6_answer(retain_all=True))
    assert sorted(missed["groups"]["missed"]) == ["H-F01", "H-F02", "H-F05", "H-F06", "H-V10-04"]
    rebuild = ailab.analyze_d6(_perfect_d6_answer(modify_money=True))
    assert len(rebuild["groups"]["over_reaction"]) == 20  # 金额用例仅来源依据更新，AI 误判为需修改
    assert rebuild["counts"]["ai_changed_existing"] == 25 and rebuild["counts"]["algorithm_changed_existing"] == 5


def test_d6_unparseable_text_reports_all_unparsed():
    out = ailab.analyze_d6("没有格式的回答")
    assert out["parsed"] is False and len(out["groups"]["unparsed"]) == 32 and out["notes"]


# ───────────── HTTP ─────────────

def test_ai_lab_http_endpoints(client):
    for kind in ALL_KINDS:
        body = client.post("/api/ai-lab/prompt", json={"kind": kind, "budget": 10}).json()
        assert body["kind"] == kind and body["chars"] == len(body["prompt"]) and body["includes"] and body["withholds"]
    assert client.post("/api/ai-lab/prompt", json={"kind": "nope"}).status_code == 422
    assert client.post("/api/ai-lab/prompt", json={"kind": "d3_select", "budget": 12}).status_code == 422
    r = client.post("/api/ai-lab/analyze", json={"kind": "d3_select", "budget": 10, "text": "FINAL_SELECTION: SC01, SC19"})
    assert r.status_code == 200 and r.json()["ai"]["ids"] == ["SC01", "SC19"]
    assert client.post("/api/ai-lab/analyze", json={"kind": "d5_compare", "text": "", "text2": ""}).status_code == 200
    assert client.post("/api/ai-lab/analyze", json={"kind": "bad"}).status_code == 422
    assert client.post("/api/ai-lab/analyze", json={"kind": "d6_impact", "text": "x" * 70000}).status_code == 422
