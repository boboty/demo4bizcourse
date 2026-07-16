from collections.abc import Iterable
from datetime import datetime, timezone

from app.models.user import User, UserStatus


class InMemoryUserRepository:
    """稳定、无外部依赖的课堂用用户仓储。"""

    def __init__(self, users: Iterable[User] = ()) -> None:
        self._users = list(users)

    @classmethod
    def with_sample_data(cls) -> "InMemoryUserRepository":
        return cls(
            [
                User(
                    id=1,
                    username="alice",
                    display_name="Alice Chen",
                    email="alice@example.com",
                    status=UserStatus.ACTIVE,
                    created_at=datetime(2024, 1, 10, 9, 30, tzinfo=timezone.utc),
                ),
                User(
                    id=2,
                    username="bob",
                    display_name=None,
                    email="bob@example.com",
                    status=UserStatus.INACTIVE,
                    created_at=datetime(2024, 2, 15, 14, 0, tzinfo=timezone.utc),
                ),
                User(
                    id=3,
                    username="carol.ops",
                    display_name="Carol 王",
                    email="carol@example.com",
                    status=UserStatus.ACTIVE,
                    created_at=datetime(2024, 3, 20, 8, 45, tzinfo=timezone.utc),
                ),
                User(
                    id=4,
                    username="dave",
                    display_name="Dave Lin",
                    email="dave@example.com",
                    status=UserStatus.PENDING,
                    created_at=datetime(2024, 4, 5, 16, 20, tzinfo=timezone.utc),
                ),
            ]
        )

    def search(
        self,
        *,
        username: str | None = None,
        status: UserStatus | None = None,
    ) -> list[User]:
        users = self._users
        if username is not None:
            normalized = username.casefold()
            users = [user for user in users if normalized in user.username.casefold()]
        if status is not None:
            users = [user for user in users if user.status == status]
        return list(users)

