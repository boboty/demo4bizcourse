import sys
from pathlib import Path

from scripts import render_round2_candidate_prompt


def test_prompt_uses_real_bundle_paths_without_inlining_page_source(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    failure = tmp_path / "failure-context.json"
    page_source = tmp_path / "page-source.html"
    screenshot = tmp_path / "failure-screenshot.png"
    failure.write_text(
        '{"failure_step":"pay_order","old_locator":{"using":"css selector","value":"#pay-now"},"target_semantic":"支付当前待付款订单"}',
        encoding="utf-8",
    )
    page_source.write_text("REAL_DOM_ONLY_MARKER", encoding="utf-8")
    screenshot.write_bytes(b"real screenshot input")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "render_round2_candidate_prompt.py",
            str(failure),
            str(page_source),
            str(screenshot),
        ],
    )

    assert render_round2_candidate_prompt.main() == 0
    output = capsys.readouterr().out

    assert str(failure.resolve()) in output
    assert str(page_source.resolve()) in output
    assert str(screenshot.resolve()) in output
    assert "REAL_DOM_ONLY_MARKER" not in output
    assert "artifacts/runs/interactive/round2-candidate.json" in output
    assert "不修改任何正式测试资产" in output
    assert "不执行 writeback" in output
    assert "不执行 Self-Heal continuation" in output
    assert '"target": "pay_button"' in output
    assert '"value": "#pay-now"' in output
