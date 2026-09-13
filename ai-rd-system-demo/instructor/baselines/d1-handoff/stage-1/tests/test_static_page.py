from pathlib import Path

STATIC_HTML = (Path(__file__).resolve().parent.parent / "static" / "index.html").read_text(encoding="utf-8")


def test_customer_name_filter_ui_exists_and_is_wired_to_the_real_api():
    assert 'id="customer-name-input"' in STATIC_HTML
    assert "/api/financing-applications" in STATIC_HTML
    assert "customer_name" in STATIC_HTML


def test_status_filter_and_export_ui_are_not_implemented_yet():
    # 进度提示里可以提到"状态筛选"/"导出"还没做（文字说明，不是控件），
    # 但不能存在真正能操作的状态筛选控件或导出按钮/真实导出请求。
    assert "status-select" not in STATIC_HTML
    assert "<select" not in STATIC_HTML
    assert "export-btn" not in STATIC_HTML
    assert "/export" not in STATIC_HTML
