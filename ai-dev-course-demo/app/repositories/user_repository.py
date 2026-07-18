from collections.abc import Iterable
from datetime import datetime, timezone

from app.models.user import User, UserStatus


class InMemoryUserRepository:
    """稳定、无外部依赖的课堂用用户仓储。"""

    def __init__(self, users: Iterable[User] = ()) -> None:
        self._users = list(users)

    @classmethod
    def with_sample_data(cls) -> "InMemoryUserRepository":
        """本地课堂 Demo 用示例数据。

        仅在应用启动时于内存中构建一次，天然幂等，不影响测试（测试使用
        conftest 自带 fixture）。共 23 条，保证默认每页 20 条时至少出现两页，
        并覆盖 active/inactive/pending 与空显示名等边界，便于演示筛选、
        分页与空值渲染。
        """

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
                User(
                    id=5,
                    username="erin",
                    display_name="Erin Zhao",
                    email="erin@example.com",
                    status=UserStatus.ACTIVE,
                    created_at=datetime(2024, 4, 12, 10, 5, tzinfo=timezone.utc),
                ),
                User(
                    id=6,
                    username="frank.ops",
                    display_name="Frank 李",
                    email="frank@example.com",
                    status=UserStatus.INACTIVE,
                    created_at=datetime(2024, 4, 18, 11, 40, tzinfo=timezone.utc),
                ),
                User(
                    id=7,
                    username="grace",
                    display_name="Grace Sun",
                    email="grace@example.com",
                    status=UserStatus.ACTIVE,
                    created_at=datetime(2024, 5, 2, 9, 0, tzinfo=timezone.utc),
                ),
                User(
                    id=8,
                    username="helen.chen",
                    display_name="Helen 陈",
                    email="helen@example.com",
                    status=UserStatus.ACTIVE,
                    created_at=datetime(2024, 5, 9, 15, 25, tzinfo=timezone.utc),
                ),
                User(
                    id=9,
                    username="iris",
                    display_name=None,
                    email="iris@example.com",
                    status=UserStatus.INACTIVE,
                    created_at=datetime(2024, 5, 16, 13, 10, tzinfo=timezone.utc),
                ),
                User(
                    id=10,
                    username="jack.ops",
                    display_name="Jack Ma",
                    email="jack@example.com",
                    status=UserStatus.ACTIVE,
                    created_at=datetime(2024, 5, 23, 8, 50, tzinfo=timezone.utc),
                ),
                User(
                    id=11,
                    username="karen",
                    display_name="Karen Wu",
                    email="karen@example.com",
                    status=UserStatus.ACTIVE,
                    created_at=datetime(2024, 6, 1, 17, 35, tzinfo=timezone.utc),
                ),
                User(
                    id=12,
                    username="leo",
                    display_name="Leo Zhang",
                    email="leo@example.com",
                    status=UserStatus.PENDING,
                    created_at=datetime(2024, 6, 8, 12, 15, tzinfo=timezone.utc),
                ),
                User(
                    id=13,
                    username="mia.chen",
                    display_name="Mia 陈",
                    email="mia@example.com",
                    status=UserStatus.ACTIVE,
                    created_at=datetime(2024, 6, 15, 14, 45, tzinfo=timezone.utc),
                ),
                User(
                    id=14,
                    username="nina",
                    display_name="",
                    email="nina@example.com",
                    status=UserStatus.ACTIVE,
                    created_at=datetime(2024, 6, 22, 10, 30, tzinfo=timezone.utc),
                ),
                User(
                    id=15,
                    username="oscar.ops",
                    display_name="Oscar Liu",
                    email="oscar@example.com",
                    status=UserStatus.INACTIVE,
                    created_at=datetime(2024, 7, 3, 9, 20, tzinfo=timezone.utc),
                ),
                User(
                    id=16,
                    username="peter",
                    display_name="Peter Wang",
                    email="peter@example.com",
                    status=UserStatus.ACTIVE,
                    created_at=datetime(2024, 7, 10, 16, 55, tzinfo=timezone.utc),
                ),
                User(
                    id=17,
                    username="quincy",
                    display_name="Quincy Ho",
                    email="quincy@example.com",
                    status=UserStatus.ACTIVE,
                    created_at=datetime(2024, 7, 17, 11, 5, tzinfo=timezone.utc),
                ),
                User(
                    id=18,
                    username="rachel.chen",
                    display_name="Rachel 陈",
                    email="rachel@example.com",
                    status=UserStatus.INACTIVE,
                    created_at=datetime(2024, 7, 24, 13, 40, tzinfo=timezone.utc),
                ),
                User(
                    id=19,
                    username="sam",
                    display_name="Sam Guo",
                    email="sam@example.com",
                    status=UserStatus.ACTIVE,
                    created_at=datetime(2024, 8, 2, 8, 15, tzinfo=timezone.utc),
                ),
                User(
                    id=20,
                    username="tina.ops",
                    display_name="Tina Xu",
                    email="tina@example.com",
                    status=UserStatus.ACTIVE,
                    created_at=datetime(2024, 8, 9, 15, 50, tzinfo=timezone.utc),
                ),
                User(
                    id=21,
                    username="victor",
                    display_name="Victor Yan",
                    email="victor@example.com",
                    status=UserStatus.INACTIVE,
                    created_at=datetime(2024, 8, 16, 10, 25, tzinfo=timezone.utc),
                ),
                User(
                    id=22,
                    username="wendy",
                    display_name="Wendy Fang",
                    email="wendy@example.com",
                    status=UserStatus.ACTIVE,
                    created_at=datetime(2024, 8, 23, 14, 0, tzinfo=timezone.utc),
                ),
                User(
                    id=23,
                    username="yuki",
                    display_name="Yuki Tanaka",
                    email="yuki@example.com",
                    status=UserStatus.ACTIVE,
                    created_at=datetime(2024, 8, 30, 9, 45, tzinfo=timezone.utc),
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

