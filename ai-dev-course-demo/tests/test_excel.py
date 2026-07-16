from io import BytesIO

import pytest
from openpyxl import load_workbook

from app.utils.excel import build_excel, clean_text


def test_clean_text_trims_existing_string_values() -> None:
    assert clean_text("  Alice  ") == "Alice"


def test_build_excel_writes_headers_and_rows() -> None:
    content = build_excel(
        ["编号", "名称"],
        [[1, "Alice"], [2, "王小明"]],
        sheet_name="示例",
    )

    worksheet = load_workbook(BytesIO(content)).active
    assert worksheet.title == "示例"
    assert list(worksheet.values) == [
        ("编号", "名称"),
        (1, "Alice"),
        (2, "王小明"),
    ]


def test_build_excel_rejects_mismatched_rows() -> None:
    with pytest.raises(ValueError, match="row length"):
        build_excel(["编号", "名称"], [[1]], sheet_name="示例")

