from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


class User(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    username: str
    display_name: str | None
    email: str
    status: UserStatus
    created_at: datetime


class UserListResponse(BaseModel):
    items: list[User]
    total: int
    page: int
    page_size: int

