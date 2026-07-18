"""课堂演示专用教学接口（/api/demo/*）。

只为四个教学状态页服务：教学故障被隔离在本路由与
app/services/demo_export_service.py 中，正式 /api/users/export 不受影响。
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, Response

from app.models.user import UserStatus
from app.services.demo_export_service import DemoExportError

router = APIRouter(prefix="/api/demo/users/export", tags=["demo"])

EXCEL_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def excel_response(content: bytes) -> Response:
    return Response(
        content=content,
        media_type=EXCEL_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="users.xlsx"'},
    )


@router.get("/null-failure")
def export_users_null_failure(
    request: Request,
    username: Annotated[str | None, Query(min_length=1)] = None,
    status: UserStatus | None = None,
) -> Response:
    """Stage 1 教学导出：普通数据可用，空姓名记录稳定触发可解释的失败。"""

    try:
        content = request.app.state.demo_export_service.export_users_null_unsafe(
            username=username,
            status=status,
        )
    except DemoExportError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return excel_response(content)


@router.get("/page-only")
def export_users_page_only(
    request: Request,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 8,
    username: Annotated[str | None, Query(min_length=1)] = None,
    status: UserStatus | None = None,
) -> Response:
    """Stage 2 教学导出：空值已修复，但错误地只导出当前页。"""

    content = request.app.state.demo_export_service.export_users_current_page(
        page=page,
        page_size=page_size,
        username=username,
        status=status,
    )
    return excel_response(content)
