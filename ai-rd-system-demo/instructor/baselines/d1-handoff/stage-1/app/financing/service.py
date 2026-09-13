from typing import Optional

from app.common.pagination import paginate
from app.financing.repository import all_applications_for_user


def _filter_by_customer_name(rows: list[dict], customer_name: Optional[str]) -> list[dict]:
    if not customer_name:
        return rows
    needle = customer_name.lower()
    return [row for row in rows if needle in row["customer_name"].lower()]


def list_applications(
    *,
    user: str,
    page: int = 1,
    page_size: int = 5,
    customer_name: Optional[str] = None,
) -> dict:
    """筛选顺序：先取 tenant 权限内数据，再筛选，最后分页（见 DECISIONS.md D-001）。"""
    rows = all_applications_for_user(user)
    rows = _filter_by_customer_name(rows, customer_name)
    return paginate(rows, page, page_size).as_dict()
