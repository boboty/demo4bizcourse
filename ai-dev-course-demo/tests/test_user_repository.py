from app.models.user import UserStatus
from app.repositories.user_repository import InMemoryUserRepository


def test_search_combines_username_and_status_filters(
    repository: InMemoryUserRepository,
) -> None:
    users = repository.search(username="ANN", status=UserStatus.ACTIVE)
    assert [user.username for user in users] == ["anna"]


def test_search_returns_a_copy(repository: InMemoryUserRepository) -> None:
    first = repository.search()
    first.clear()
    assert len(repository.search()) == 3

