from typing import Optional

from app.common.export_jobs import ExportJob, export_queue
from app.common.pagination import paginate
from app.common.security import allowed_tenants
from app.financing.repository import all_applications_for_user

EXPORT_FIELDS = ("id", "customer_name", "status", "amount")

# 放款处理导出资格规则的唯一事实源是 docs/rules/export_eligibility.md，不在这里重复整段
# 规则原文；改动这个集合前先读那份文件。
EXPORT_ELIGIBLE_STATUSES = {"APPROVED", "FUNDED"}


def _eligible_for_export(rows: list[dict]) -> list[dict]:
    return [row for row in rows if row["status"] in EXPORT_ELIGIBLE_STATUSES]


def _filter_by_customer_name(rows: list[dict], customer_name: Optional[str]) -> list[dict]:
    if not customer_name:
        return rows
    needle = customer_name.lower()
    return [row for row in rows if needle in row["customer_name"].lower()]


def _filter_by_status(rows: list[dict], status: Optional[str]) -> list[dict]:
    if not status:
        return rows
    return [row for row in rows if row["status"] == status]


def _filtered_rows(*, user: str, customer_name: Optional[str], status: Optional[str]) -> list[dict]:
    """筛选顺序：先取 tenant 权限内数据，再筛选。"""
    rows = all_applications_for_user(user)
    rows = _filter_by_customer_name(rows, customer_name)
    rows = _filter_by_status(rows, status)
    return rows


def list_applications(
    *,
    user: str,
    page: int = 1,
    page_size: int = 5,
    customer_name: Optional[str] = None,
    status: Optional[str] = None,
) -> dict:
    rows = _filtered_rows(user=user, customer_name=customer_name, status=status)
    return paginate(rows, page, page_size).as_dict()


def export_applications(
    *,
    user: str,
    customer_name: Optional[str] = None,
    status: Optional[str] = None,
) -> ExportJob:
    """导出当前筛选结果中允许放款导出的部分（不分页），并在 payload 里保留筛选条件和用户权限范围。

    列表查询（list_applications）不受本函数影响：SUBMITTED / REJECTED 依旧可以被筛选查到，
    只是不会出现在这里返回的导出 payload 里。
    """
    rows = _filtered_rows(user=user, customer_name=customer_name, status=status)
    eligible_rows = _eligible_for_export(rows)
    export_rows = [{field: row[field] for field in EXPORT_FIELDS} for row in eligible_rows]
    payload = {
        "filters": {"customer_name": customer_name, "status": status},
        "requested_by": user,
        "tenant_scope": sorted(allowed_tenants(user)),
        "rows": export_rows,
    }
    return export_queue.enqueue("financing_applications_export", payload)
