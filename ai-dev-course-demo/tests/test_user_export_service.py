from datetime import datetime, timezone

import pytest

from app.models.user import User, UserStatus
from app.repositories.user_repository import InMemoryUserRepository
from app.services.user_export_service import (
    MAX_EXPORT_ROWS,
    ExportLimitExceeded,
    UserExportService,
)
from app.services.user_service import UserService


def make_user(user_id: int, *, display_name: str | None = "Demo User") -> User:
    return User(
        id=user_id,
        username=f"user{user_id}",
        display_name=display_name,
        email=f"user{user_id}@example.com",
        status=UserStatus.ACTIVE,
        created_at=datetime(2024, 6, 1, 12, 30, tzinfo=timezone.utc),
    )


def make_export_service(users: list[User]) -> UserExportService:
    repository = InMemoryUserRepository(users)
    return UserExportService(UserService(repository))


def test_null_display_name_is_mapped_to_empty_string() -> None:
    user = make_user(1, display_name=None)

    row = UserExportService._to_row(user)

    assert row[2] == ""


def test_exactly_maximum_rows_can_be_exported() -> None:
    users = [make_user(index) for index in range(1, MAX_EXPORT_ROWS + 1)]
    service = make_export_service(users)

    content = service.export_users()

    assert content.startswith(b"PK")


def test_more_than_maximum_rows_is_rejected() -> None:
    users = [make_user(index) for index in range(1, MAX_EXPORT_ROWS + 2)]
    service = make_export_service(users)

    with pytest.raises(ExportLimitExceeded, match="10001.*10000"):
        service.export_users()
