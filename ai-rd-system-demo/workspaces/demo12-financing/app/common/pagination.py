from dataclasses import dataclass
from typing import Sequence, TypeVar

T = TypeVar("T")

@dataclass(frozen=True)
class Page:
    items: list
    page: int
    page_size: int
    total: int

    def as_dict(self) -> dict:
        return {"items": self.items, "page": self.page, "page_size": self.page_size, "total": self.total}


def paginate(items: Sequence[T], page: int, page_size: int) -> Page:
    if page < 1:
        raise ValueError("page must be >= 1")
    if page_size < 1 or page_size > 100:
        raise ValueError("page_size must be between 1 and 100")
    start = (page - 1) * page_size
    end = start + page_size
    return Page(list(items[start:end]), page, page_size, len(items))
