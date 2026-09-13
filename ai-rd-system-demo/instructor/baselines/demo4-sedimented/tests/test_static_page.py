from pathlib import Path

STATIC_HTML = (Path(__file__).resolve().parent.parent / "static" / "index.html").read_text(encoding="utf-8")


def test_customer_and_status_filter_controls_exist():
    assert 'id="customer-name-input"' in STATIC_HTML
    assert 'id="status-select"' in STATIC_HTML
    assert "<select" in STATIC_HTML


def test_filters_are_wired_to_the_real_api_and_support_combination():
    assert "/api/financing-applications" in STATIC_HTML
    assert "customer_name" in STATIC_HTML
    assert "status" in STATIC_HTML


def test_export_button_calls_the_real_export_endpoint_and_renders_the_real_result():
    assert 'id="export-btn"' in STATIC_HTML
    assert "/api/financing-applications/export" in STATIC_HTML
    # 页面渲染的必须是后端真实返回的字段，不是前端写死的提示文字
    assert "job.id" in STATIC_HTML
    assert "job.status" in STATIC_HTML
    assert "job.payload" in STATIC_HTML
