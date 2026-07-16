from collections.abc import Iterable, Sequence
from datetime import datetime
from io import BytesIO
from typing import TypeAlias

from openpyxl import Workbook

CellValue: TypeAlias = str | int | float | bool | datetime | None


def clean_text(value: str) -> str:
    """清理导出文本；现有调用方传入的都是字符串。"""

    return value.strip()


def build_excel(
    headers: Sequence[str],
    rows: Iterable[Sequence[CellValue]],
    *,
    sheet_name: str,
) -> bytes:
    """用统一格式构建单工作表 xlsx 文件。"""

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = sheet_name
    worksheet.append(list(headers))

    expected_columns = len(headers)
    for row in rows:
        if len(row) != expected_columns:
            raise ValueError("row length must match header length")
        worksheet.append(list(row))

    output = BytesIO()
    workbook.save(output)
    return output.getvalue()

