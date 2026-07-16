from app.models.user import UserStatus
from app.repositories.user_repository import InMemoryUserRepository
from app.services.user_service import UserService


def test_list_users_paginates_filtered_results(
    repository: InMemoryUserRepository,
) -> None:
    service = UserService(repository)

    result = service.list_users(
        page=2,
        page_size=1,
        status=UserStatus.ACTIVE,
    )

    assert result.total == 2
    assert result.page == 2
    assert result.page_size == 1
    assert [user.username for user in result.items] == ["brian"]


def test_search_users_preserves_repository_order(
    repository: InMemoryUserRepository,
) -> None:
    service = UserService(repository)
    assert [user.id for user in service.search_users()] == [10, 11, 12]

