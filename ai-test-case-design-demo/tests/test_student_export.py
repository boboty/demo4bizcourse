"""学员材料包：独立性、可复制性，以及对讲师答案的严格排除。"""
import json
import re
import shutil
import zipfile

import pytest

from app import ailab
from app.assets import DEFAULT_ROOT, load
from app.student_export import (DENY_FILES, PACKAGES, ExportError, _check_input_path, build_package, export_all,
                                instructor_fingerprints)


@pytest.fixture(scope="module")
def exported(tmp_path_factory):
    out = tmp_path_factory.mktemp("packages")
    export_all(out)
    return out


def folders(out):
    return sorted(p for p in out.iterdir() if p.is_dir())


def read_all(folder):
    return {p.name: p.read_text(encoding="utf-8") for p in folder.iterdir()}


def test_two_independent_packages_with_html_and_txt_only(exported):
    assert [p.name for p in folders(exported)] == ["demo3-scenario-selection", "demo6-incremental-update"]
    for folder in folders(exported):
        assert sorted(p.name for p in folder.iterdir()) == ["prompts.txt", "student-package.html"]
    for folder in folders(exported):
        html = (folder / "student-package.html").read_text(encoding="utf-8")
        assert not re.search(r'(?:href|src)="(?!#)', html), "材料包必须单文件自洽，不引用外部或另一套材料"
        assert "http://" not in html and "https://" not in html


def test_no_instructor_content_anywhere_in_output(exported):
    fingerprints = instructor_fingerprints(DEFAULT_ROOT)
    assert len(fingerprints) > 20, "讲师参考指纹应非空，否则泄漏扫描形同虚设"
    for folder in folders(exported):
        for name, text in read_all(folder).items():
            assert "instructor" not in text and "REFERENCE" not in text, name
            for fingerprint in fingerprints:
                assert fingerprint not in text, (name, fingerprint)
    reference = load("practice/instructor/demo3_scenario_design_reference.json")
    assert ", ".join(reference["suggested_selection_under_budget_15"]) not in "".join(
        t for f in folders(exported) for t in read_all(f).values())


def test_demo3_package_withholds_finance_v11_and_sc36_hint(exported):
    text = "".join(read_all(exported / "demo3-scenario-selection").values())
    for token in PACKAGES[3]["forbidden"]:
        assert token not in text, token
    assert "课堂中应人工补回" not in text
    for budget in (10, 15, 20):
        assert ailab.build_prompt("d3_select", budget)["prompt"] in (exported / "demo3-scenario-selection" / "prompts.txt").read_text(encoding="utf-8")


def test_demo6_package_has_validated_history_and_two_prompts(exported):
    folder = exported / "demo6-incremental-update"
    txt = (folder / "prompts.txt").read_text(encoding="utf-8")
    assert ailab.build_prompt("d6_impact")["prompt"] in txt
    assert "最多25条" in txt or "回归用例上限：25" in txt
    html = (folder / "student-package.html").read_text(encoding="utf-8")
    for case_id in ("H-F01", "H-M01", "H-V10-06"):
        assert case_id in html
    additions = load("history/v1_1_additions.json")
    assert not any(c["case_id"] in html for c in additions["cases"] if c["case_id"].startswith("N"))


def test_every_copy_button_has_a_nonempty_source(exported):
    for folder in folders(exported):
        html = (folder / "student-package.html").read_text(encoding="utf-8")
        targets = re.findall(r'data-copy-from="([^"]+)"', html)
        assert targets
        for target in targets:
            assert re.search(r'id="%s"' % re.escape(target), html), target
        assert len(re.findall(r"<textarea[^>]*hidden", html)) >= 5


def test_guard_rejects_instructor_and_answer_files():
    for bad in ("practice/instructor/demo3_scenario_design_reference.json", "frozen/demo5_review_round1.json",
                "cases/v1_0_executable.json", "../outside.json", "/etc/passwd") + tuple(DENY_FILES):
        with pytest.raises(ExportError):
            _check_input_path(bad)


def test_student_task_pointing_at_instructor_file_is_refused(tmp_path):
    root = tmp_path / "assets"
    shutil.copytree(DEFAULT_ROOT, root)
    path = root / "practice/student/demo3_scenario_design.json"
    task = json.loads(path.read_text(encoding="utf-8"))
    task["input_files"].append("practice/instructor/demo3_scenario_design_reference.json")
    path.write_text(json.dumps(task, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ExportError):
        build_package(3, root)


def test_leaked_instructor_text_in_inputs_blocks_all_output(tmp_path):
    root = tmp_path / "assets"
    shutil.copytree(DEFAULT_ROOT, root)
    reference = json.loads((root / "practice/instructor/demo6_incremental_update_reference.json").read_text(encoding="utf-8"))
    leaked = next(a["reason"] for a in reference["sample_derived_actions"] if a["action"] == "add")
    path = root / "scenarios/candidates_v1_0.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["scenarios"][0]["title"] = leaked
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    out = tmp_path / "out"
    with pytest.raises(ExportError):
        export_all(out, root)
    assert not out.exists(), "扫描失败时不得写出任何文件"


def test_export_is_deterministic(tmp_path):
    first, second = tmp_path / "a", tmp_path / "b"
    export_all(first)
    export_all(second)
    for path in first.rglob("*"):
        if path.is_file():
            assert path.read_bytes() == (second / path.relative_to(first)).read_bytes()


def test_demo6_hides_disposition_hints(exported):
    text = "".join(read_all(exported / "demo6-incremental-update").values())
    for hint in ("migration_criteria", "迁移判断标准", "legacy_unconditional_gate", "baseline_status", "基线状态",
                 "v1_1_additions", "target_additions"):
        assert hint not in text, hint
    criteria = load("history/v1_1_rule_diff.json")["migration_criteria"]
    for item in criteria:
        assert item["derive"] not in text
    # 原始业务资产不变：提示字段仍在源文件里
    assert "migration_criteria" in load("history/v1_1_rule_diff.json")


def test_each_package_has_its_own_zip_with_only_html_and_txt(exported):
    zips = sorted(p.name for p in exported.glob("*.zip"))
    assert zips == ["demo3-scenario-selection.zip", "demo6-incremental-update.zip"]
    for archive_path in exported.glob("*.zip"):
        slug = archive_path.stem
        with zipfile.ZipFile(str(archive_path)) as archive:
            assert archive.testzip() is None
            assert sorted(archive.namelist()) == [slug + "/prompts.txt", slug + "/student-package.html"]
            for name in archive.namelist():
                assert archive.read(name) == (exported / name).read_bytes(), "ZIP 内容必须与文件夹一致"
