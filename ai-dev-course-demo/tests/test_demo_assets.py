from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO1 = ROOT / "demo_assets" / "demo1"
DEMO2 = ROOT / "demo_assets" / "demo2"


def test_live_prompt_is_the_same_task_package() -> None:
    assert (DEMO2 / "01_live_prompt.md").read_bytes() == (
        DEMO1 / "03_task_package.md"
    ).read_bytes()


def test_demo1_required_files_exist() -> None:
    required = {
        "01_ambiguous_request.md",
        "02_direct_prompt.md",
        "03_task_package.md",
        "04_comparison.md",
        "05_minimum_task_package.md",
        "06_practice_card.md",
        "outputs/direct_run.md",
        "outputs/task_package_run.md",
    }
    assert all((DEMO1 / relative_path).is_file() for relative_path in required)


def test_task_package_has_exactly_six_top_level_sections() -> None:
    content = (DEMO1 / "03_task_package.md").read_text(encoding="utf-8")
    headings = [line for line in content.splitlines() if line.startswith("# ")]
    assert headings == ["# 背景", "# 目标", "# 输入", "# 约束", "# 输出", "# 验收"]


def test_all_seven_nodes_contain_the_four_required_parts() -> None:
    expected_names = [
        "01_read_project.md",
        "02_plan.md",
        "03_modify_code.md",
        "04_generate_tests.md",
        "05_validation_failed.md",
        "06_fix_and_pass.md",
        "07_change_summary.md",
    ]
    required_headings = {
        "## 关键终端日志",
        "## 截图建议范围",
        "## 讲师应观察的证据",
        "## 一句讲解提示",
    }

    node_directory = DEMO2 / "nodes"
    assert sorted(path.name for path in node_directory.glob("*.md")) == expected_names
    for name in expected_names:
        content = (node_directory / name).read_text(encoding="utf-8")
        assert required_headings.issubset(content.splitlines())


def test_three_pause_messages_are_present() -> None:
    expected_messages = {
        "02_plan.md": "计划不是为了让AI看起来更专业，而是在写代码之前制造一个成本最低的人审点。",
        "05_validation_failed.md": "这就是任务包里验收要素存在的原因。AI写出代码并不代表任务完成，验证结果会重新进入执行过程。",
        "07_change_summary.md": "变更说明是本次执行接入代码评审、团队协作和后续审计的接口。",
    }
    for name, message in expected_messages.items():
        content = (DEMO2 / "nodes" / name).read_text(encoding="utf-8")
        assert message in content
