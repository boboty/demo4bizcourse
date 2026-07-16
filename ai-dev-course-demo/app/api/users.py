from typing import Annotated

from fastapi import APIRouter, Query, Request

from app.models.user import UserListResponse, UserStatus

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=UserListResponse)
def list_users(
    request: Request,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    username: Annotated[str | None, Query(min_length=1)] = None,
    status: UserStatus | None = None,
) -> UserListResponse:
    """返回符合筛选条件的一页用户。"""

    return request.app.state.user_service.list_users(
        page=page,
        page_size=page_size,
        username=username,
        status=status,
    )

