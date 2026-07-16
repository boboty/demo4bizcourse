from app.models.user import User, UserStatus
from app.services.user_service import UserService
from app.utils.excel import CellValue, build_excel, clean_text

MAX_EXPORT_ROWS = 10_000
USER_EXPORT_HEADERS = (
    "用户ID",
    "用户名",
    "显示名称",
    "邮箱",
    "状态",
    "创建时间",
)


class ExportLimitExceeded(ValueError):
    pass


class UserExportService:
    def __init__(self, user_service: UserService) -> None:
        self._user_service = user_service

    def export_users(
        self,
        *,
        username: str | None = None,
        status: UserStatus | None = None,
    ) -> bytes:
        users = self._user_service.search_users(username=username, status=status)
        if len(users) > MAX_EXPORT_ROWS:
            raise ExportLimitExceeded(
                f"导出结果为{len(users)}行，超过最大限制{MAX_EXPORT_ROWS}行"
            )

        rows = [self._to_row(user) for user in users]
        return build_excel(USER_EXPORT_HEADERS, rows, sheet_name="用户列表")

    @staticmethod
    def _to_row(user: User) -> list[CellValue]:
        return [
            user.id,
            clean_text(user.username),
            clean_text(user.display_name),
            clean_text(user.email),
            user.status.value,
            user.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        ]
