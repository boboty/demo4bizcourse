from app.models.user import User, UserListResponse, UserStatus
from app.repositories.user_repository import InMemoryUserRepository


class UserService:
    def __init__(self, repository: InMemoryUserRepository) -> None:
        self._repository = repository

    def search_users(
        self,
        *,
        username: str | None = None,
        status: UserStatus | None = None,
    ) -> list[User]:
        """用户筛选的唯一服务层入口，供列表和后续批量能力复用。"""

        return self._repository.search(username=username, status=status)

    def list_users(
        self,
        *,
        page: int,
        page_size: int,
        username: str | None = None,
        status: UserStatus | None = None,
    ) -> UserListResponse:
        matched = self.search_users(username=username, status=status)
        start = (page - 1) * page_size
        end = start + page_size
        return UserListResponse(
            items=matched[start:end],
            total=len(matched),
            page=page,
            page_size=page_size,
        )

