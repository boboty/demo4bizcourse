import json
import shutil
from pathlib import Path

import pytest

from app.assets import DEFAULT_ROOT, AssetValidationError, project_demo2, validate_assets


def copied_assets(tmp_path):
    target = tmp_path / "assets"
    shutil.copytree(DEFAULT_ROOT, target)
    return target


def read(root, relative):
    path = root / relative
    return json.loads(path.read_text(encoding="utf-8"))


def write(root, relative, value):
    (root / relative).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def test_canonical_assets_are_ready_and_demo2_projection_is_v1_0_only():
    report = validate_assets()
    assert report["status"] == "READY"
    assert (report["scenarios"], report["cases"], report["case_passed"]) == (45, 20, 20)
    projection = project_demo2()
    assert projection["version"] == "1.0"
    assert set(projection["structured_analysis"]) == {
        "roles", "inputs", "flow", "states", "rules", "external_dependencies", "risks", "questions"
    }
    assert len(projection["scenarios"]) == 41
    assert sum(len(ids) for columns in projection["scenario_map"]["cells"].values() for ids in columns.values()) == 41
    serialized = json.dumps(projection, ensure_ascii=False)
    for forbidden in ("F10", "F20", "F30", "P11", "P31", "P41", "极速退款", "15日", "R-PROMO-RECALC"):
        assert forbidden not in serialized


def test_asset_validator_rejects_missing_required_material(tmp_path):
    root = copied_assets(tmp_path)
    (root / "finance/after_sales_funds.json").unlink()
    with pytest.raises(AssetValidationError, match="required asset missing"):
        validate_assets(root)


def test_asset_validator_rejects_bad_scenario_rule_reference(tmp_path):
    root = copied_assets(tmp_path)
    data = read(root, "scenarios/candidates.json")
    data["scenarios"][0]["rule_ids"] = ["R-NOT-FOUND"]
    write(root, "scenarios/candidates.json", data)
    with pytest.raises(AssetValidationError, match="references missing rule IDs"):
        validate_assets(root)


def test_asset_validator_rejects_unknown_source_id(tmp_path):
    root = copied_assets(tmp_path)
    data = read(root, "business/rules.json")
    data["rules"][0]["source_ids"] = ["P-UNKNOWN"]
    write(root, "business/rules.json", data)
    with pytest.raises(AssetValidationError, match="unknown source IDs"):
        validate_assets(root)


def test_asset_validator_rejects_missing_frozen_marker(tmp_path):
    root = copied_assets(tmp_path)
    data = read(root, "frozen/demo2_direct_generation.json")
    data["frozen"] = False
    write(root, "frozen/demo2_direct_generation.json", data)
    with pytest.raises(AssetValidationError, match="frozen=true"):
        validate_assets(root)


def test_asset_validator_rejects_v1_1_leak_in_v1_0_snapshot(tmp_path):
    root = copied_assets(tmp_path)
    data = read(root, "business/rules_v1_0.json")
    data["rules"].append(read(root, "business/rules.json")["rules"][-1])
    write(root, "business/rules_v1_0.json", data)
    with pytest.raises(AssetValidationError, match="V1.0 snapshots differ|V1.0 snapshot leaks"):
        validate_assets(root)
