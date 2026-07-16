from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, Response

from app.models.user import UserListResponse, UserStatus
from app.services.user_export_service import ExportLimitExceeded

router = APIRouter(prefix="/api/users", tags=["users"])

EXCEL_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/export")
def export_users(
    request: Request,
    username: Annotated[str | None, Query(min_length=1)] = None,
    status: UserStatus | None = None,
) -> Response:
    """按列表筛选口径导出全部匹配用户。"""

    try:
        content = request.app.state.user_export_service.export_users(
            username=username,
            status=status,
        )
    except ExportLimitExceeded as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return Response(
        content=content,
        media_type=EXCEL_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="users.xlsx"'},
    )


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
