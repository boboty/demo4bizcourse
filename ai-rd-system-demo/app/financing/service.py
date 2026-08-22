from app.common.pagination import paginate
from app.financing.repository import all_applications_for_user


def list_applications(*, user: str, page: int = 1, page_size: int = 5, customer_name: str | None = None, status: str | None = None) -> dict:
    rows = all_applications_for_user(user)
    if customer_name:
        needle = customer_name.strip().lower()
        rows = [row for row in rows if needle in row["customer_name"].lower()]
    if status:
        rows = [row for row in rows if row["status"] == status]
    return paginate(rows, page, page_size).as_dict()
