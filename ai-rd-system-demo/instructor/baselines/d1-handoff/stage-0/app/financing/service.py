from app.common.pagination import paginate
from app.financing.repository import all_applications_for_user


def list_applications(*, user: str, page: int = 1, page_size: int = 5) -> dict:
    """Baseline behavior: list authorized applications with existing pagination only."""
    rows = all_applications_for_user(user)
    return paginate(rows, page, page_size).as_dict()
