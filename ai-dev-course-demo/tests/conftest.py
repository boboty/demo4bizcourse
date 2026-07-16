from collections.abc import Iterator
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.models.user import User, UserStatus
from app.repositories.user_repository import InMemoryUserRepository


@pytest.fixture
def sample_users() -> list[User]:
    return [
        User(
            id=10,
            username="anna",
            display_name="Anna 安",
            email="anna@example.com",
            status=UserStatus.ACTIVE,
            created_at=datetime(2024, 5, 1, 8, 0, tzinfo=timezone.utc),
        ),
        User(
            id=11,
            username="ann.ops",
            display_name=None,
            email="ann.ops@example.com",
            status=UserStatus.INACTIVE,
            created_at=datetime(2024, 5, 2, 9, 15, tzinfo=timezone.utc),
        ),
        User(
            id=12,
            username="brian",
            display_name="Brian",
            email="brian@example.com",
            status=UserStatus.ACTIVE,
            created_at=datetime(2024, 5, 3, 10, 30, tzinfo=timezone.utc),
        ),
    ]


@pytest.fixture
def repository(sample_users: list[User]) -> InMemoryUserRepository:
    return InMemoryUserRepository(sample_users)


@pytest.fixture
def client(repository: InMemoryUserRepository) -> Iterator[TestClient]:
    with TestClient(create_app(repository)) as test_client:
        yield test_client

