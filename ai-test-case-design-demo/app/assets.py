"""Read and validate the stable JSON fixtures used by the demo engine."""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from app.engine import calculate_finance_sequence, execute_v1_0_cases
from app.executor import execute_cases
DEFAULT_ROOT = Path(__file__).resolve().parents[1] / "demo_assets"
REQUIRED = (
    "prd/prd_v1_0.json", "prd/prd_v1_1.json", "business/rules.json",
    "business/rules_v1_0.json", "business/analysis.json", "scenarios/candidates.json",
    "scenarios/candidates_v1_0.json", "cases/v1_0_executable.json",
    "finance/after_sales_funds.json", "frozen/demo2_direct_generation.json",
    "frozen/demo5_review_round1.json", "frozen/demo5_review_round2.json",
    "history/v1_0_validated_baseline.json", "history/v1_1_rule_diff.json",
    "history/v1_1_additions.json", "practice/student/demo3_scenario_design.json",
    "practice/student/demo6_incremental_update.json",
    "practice/instructor/demo3_scenario_design_reference.json",
    "practice/instructor/demo6_incremental_update_reference.json",
)
class AssetValidationError(ValueError):
    """Raised when stable fixture files do not satisfy their data contract."""
def load(relative: str, root: Optional[Path] = None) -> Any:
    """Load a JSON fixture relative to the supplied asset root."""
    base = Path(root) if root is not None else DEFAULT_ROOT
    path = (base / relative).resolve()
    if not path.is_relative_to(base.resolve()):
        raise AssetValidationError("asset path escapes the asset root: %s" % relative)
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)
def _fail(message: str) -> None:
    raise AssetValidationError(message)
def _unique(rows: List[Dict[str, Any]], key: str, label: str) -> None:
    values = [row.get(key) for row in rows]
    if None in values or len(values) != len(set(values)):
        _fail("%s IDs must be present and unique" % label)
def _versioned_rules(rows: List[Dict[str, Any]], version: str) -> List[Dict[str, Any]]:
    result = []
    for rule in rows:
        if version not in rule.get("versions", []):
            continue
        item = dict(rule)
        item["versions"] = [version]
        for field, alternate in (("statement", "versioned_statement"), ("evidence_status", "versioned_evidence"), ("source_ids", "versioned_sources")):
            item[field] = rule.get(alternate, {}).get(version, rule.get(field))
        for field in ("versioned_statement", "versioned_evidence", "versioned_sources", "versioned_statements", "superseded_in"):
            item.pop(field, None)
        result.append(item)
    return result
def validate_assets(root: Optional[Path] = None) -> Dict[str, Any]:
    """Validate required fixtures, IDs, references, versions, money, and frozen outputs."""
    base = Path(root) if root is not None else DEFAULT_ROOT
    for relative in REQUIRED:
        if not (base / relative).is_file():
            _fail("required asset missing: %s" % relative)
    try:
        docs = {name: load(name, base) for name in REQUIRED}
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        _fail("asset cannot be loaded: %s" % exc)
    v10, v11 = docs["prd/prd_v1_0.json"], docs["prd/prd_v1_1.json"]
    canonical_rules = docs["business/rules.json"]["rules"]
    fin_rules = docs["finance/after_sales_funds.json"]["rules"]
    canonical_scenes = docs["scenarios/candidates.json"]["scenarios"]
    rules10 = docs["business/rules_v1_0.json"]["rules"]
    scenes10 = docs["scenarios/candidates_v1_0.json"]["scenarios"]
    cases = docs["cases/v1_0_executable.json"]["cases"]
    history = docs["history/v1_0_validated_baseline.json"]
    additions = docs["history/v1_1_additions.json"]
    _unique(canonical_rules, "rule_id", "rule")
    _unique(fin_rules, "rule_id", "finance rule")
    _unique(v10.get("paragraphs", []), "source_id", "V1.0 paragraph")
    _unique(v11.get("paragraphs", []), "source_id", "V1.1 paragraph")
    _unique(v11.get("paragraphs_added", []), "source_id", "V1.1 added paragraph")
    _unique(canonical_scenes, "scenario_id", "scenario")
    _unique(history["scenarios"], "scenario_id", "history scenario")
    _unique(additions["scenarios"], "scenario_id", "target scenario")
    _unique(cases, "case_id", "case")
    _unique(history["cases"], "case_id", "history case")
    _unique(additions["cases"], "case_id", "target case")
    if len({row["rule_id"] for row in canonical_rules + fin_rules}) != len(canonical_rules) + len(fin_rules):
        _fail("business and finance rule IDs must be globally unique")
    all_rules = {row["rule_id"] for row in canonical_rules + fin_rules}
    for scene in canonical_scenes + history["scenarios"] + additions["scenarios"]:
        missing = set(scene.get("rule_ids", [])) - all_rules
        if missing:
            _fail("%s references missing rule IDs: %s" % (scene.get("scenario_id"), sorted(missing)))
    all_scenarios = {row["scenario_id"] for row in canonical_scenes}
    all_scenarios.update(row["scenario_id"] for row in history["scenarios"])
    all_scenarios.update(row["scenario_id"] for row in additions["scenarios"])
    if len(all_scenarios) != len(canonical_scenes) + len(history["scenarios"]) + len(additions["scenarios"]):
        _fail("scenario IDs must be globally unique across candidate and history assets")
    all_cases = cases + history["cases"] + additions["cases"]
    _unique(all_cases, "case_id", "global case")
    for case in all_cases:
        missing = set(case.get("rule_ids", case.get("source_rule_ids", []))) - all_rules
        missing |= set(case.get("source_rule_ids", [])) - all_rules
        if missing:
            _fail("%s references missing rule IDs: %s" % (case.get("case_id"), sorted(missing)))
        missing_scenarios = set(case.get("scenario_ids", [])) - all_scenarios
        if missing_scenarios:
            _fail("%s references missing scenarios: %s" % (case.get("case_id"), sorted(missing_scenarios)))
    source_ids = {p["source_id"] for doc in (v10, v11) for p in doc.get("paragraphs", [])}
    source_ids.update(p["source_id"] for p in v11.get("paragraphs_added", []))
    source_ids.update(all_rules)
    source_ids.update((v10["document_id"] + "@1.0", v11["document_id"] + "@1.1", docs["finance/after_sales_funds.json"]["document_id"]))
    def check_sources(value: Any, context: str = "asset") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "source_ids" and isinstance(child, list):
                    missing = [item for item in child if item not in source_ids and not str(item).startswith("executor_report:")]
                    if missing:
                        _fail("%s has unknown source IDs: %s" % (context, missing))
                elif key == "source_id" and isinstance(child, str) and child not in source_ids:
                    _fail("%s has unknown source ID: %s" % (context, child))
                else:
                    check_sources(child, context)
        elif isinstance(value, list):
            for child in value:
                check_sources(child, context)
    for name, doc in docs.items():
        check_sources(doc, name)
    projected_rules = _versioned_rules(canonical_rules, "1.0")
    projected_scenes = [s for s in canonical_scenes if "1.0" in s.get("versions", [])]
    if rules10 != projected_rules or scenes10 != projected_scenes:
        _fail("V1.0 snapshots differ from the canonical version-filtered projection")
    if any("1.1" in row.get("versions", []) for row in rules10 + scenes10):
        _fail("V1.0 snapshot leaks V1.1 assets")
    v10_text = json.dumps(rules10 + scenes10, ensure_ascii=False)
    if any(token in v10_text for token in ("P11", "P31", "P41", "R-FAST-REFUND", "R-PROMO-RECALC", "15日")):
        _fail("V1.0 snapshot contains future-version sources or rules")
    changes = sorted(item["change_id"] for item in v11.get("changes", []))
    if changes != ["C10", "C20", "C30"]:
        _fail("V1.1 must contain exactly C10, C20, and C30")
    diff = docs["history/v1_1_rule_diff.json"].get("rule_diff", [])
    if sorted(item.get("change_id") for item in diff) != ["C10", "C20", "C30"]:
        _fail("rule diff must contain exactly the three PRD changes")
    for item in diff:
        missing = set(item.get("affected_rule_ids", [])) - all_rules
        if missing:
            _fail("rule diff references missing rules: %s" % sorted(missing))
    for name in ("frozen/demo2_direct_generation.json", "frozen/demo5_review_round1.json", "frozen/demo5_review_round2.json"):
        if docs[name].get("frozen") is not True:
            _fail("frozen output lacks frozen=true: %s" % name)
    case_data = docs["cases/v1_0_executable.json"]
    if case_data.get("count") != len(cases):
        _fail("case count does not match case rows")
    report = execute_v1_0_cases(case_data)
    if report["total"] != len(cases):
        _fail("execution count does not match case rows")
    if report["failed"]:
        _fail("V1.0 executable cases do not match expectations")
    if len(canonical_scenes) < 40 or len(canonical_scenes) > 80:
        _fail("candidate scenario count must be between 40 and 80")
    if docs["scenarios/candidates_v1_0.json"].get("total") != len(scenes10):
        _fail("V1.0 scenario snapshot count does not match rows")
    if docs["scenarios/candidates.json"].get("theoretical_product", {}).get("count") != 432:
        _fail("scenario combination count must remain 432")
    worked = docs["finance/after_sales_funds.json"]["worked_example"]
    expected_values = {"gross_total": "357.00", "original_discount": "50.00", "paid": "307.00", "remaining_gross": "258.00", "recalculated_discount": "0.00", "refund": "49.00", "assumed_proportional_refund": "85.13", "difference": "36.13"}
    if any(worked.get(key) != value for key, value in expected_values.items()):
        _fail("classic finance example does not match fixed business facts")
    order = {"items": worked["items"], "promotion": {"threshold": "300.00", "discount": worked["original_discount"], "enabled": True}, "original_discount": worked["original_discount"], "paid": worked["paid"]}
    sku_sequence = [item.split(":", 1)[0] for item in docs["finance/after_sales_funds.json"]["cumulative_example"]["refund_order"]]
    finance_rows = calculate_finance_sequence(order, [[sku] for sku in sku_sequence])
    if [row["refund"] for row in finance_rows] != ["49.00", "59.00", "199.00"] or finance_rows[-1]["cumulative_refunded"] != worked["paid"]:
        _fail("cumulative finance example does not match the executable finance rule")
    if execute_cases(history['cases'], '1.0')['failed']:
        _fail('history execution does not match independently verified expectations')
    if execute_cases(additions['cases'], '1.1')['failed']:
        _fail('target additions execution does not match expected behavior')
    return {"status": "READY", "rules": len(canonical_rules), "scenarios": len(canonical_scenes), "cases": report["total"], "case_passed": report["passed"], "history_cases": len(history["cases"]), "target_additions": len(additions["cases"])}
def project_demo2(root: Optional[Path] = None) -> Dict[str, Any]:
    """Return only V1.0 materials for the first-generation and structured-analysis lesson."""
    prd = load("prd/prd_v1_0.json", root)
    analysis = load("business/analysis.json", root)
    rules = load("business/rules_v1_0.json", root)["rules"]
    scenes = load("scenarios/candidates_v1_0.json", root)["scenarios"]
    direct = load("frozen/demo2_direct_generation.json", root)
    stage_names = {"apply": "申请", "review": "审核", "ship": "寄回", "receive": "质检", "inspect": "质检", "refund": "退款", "close": "完结"}
    row_names = {"normal": "正常", "equivalence": "分支", "state": "分支", "combination": "分支", "exception": "异常", "boundary": "边界", "external_dependency": "外部依赖"}
    columns = ["申请", "审核", "寄回", "质检", "退款", "完结"]
    rows = ["正常", "分支", "异常", "边界", "外部依赖"]
    cells = {column: {row: [] for row in rows} for column in columns}
    for scene in scenes:
        column = stage_names.get(scene.get("stage"))
        row = row_names.get(scene.get("category"))
        if column and row:
            cells[column][row].append(scene["scenario_id"])
    mapped = [sid for row_cells in cells.values() for entries in row_cells.values() for sid in entries]
    if len(mapped) != len(scenes) or set(mapped) != {scene["scenario_id"] for scene in scenes}:
        _fail("each V1.0 scenario must appear in exactly one scene-map cell")
    axes = {key: analysis[source] for key, source in (("roles", "roles"), ("inputs", "inputs"), ("flow", "flow"), ("states", "states"), ("external_dependencies", "external_dependencies"), ("risks", "risks"), ("questions", "questions"))}
    axes["rules"] = rules
    return {"version": "1.0", "prd": prd, "direct_generation": direct, "structured_analysis": axes, "rules": rules, "scenario_map": {"columns": columns, "rows": rows, "cells": cells}, "scenarios": scenes}
