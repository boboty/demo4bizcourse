"""课堂演示专用导出编排（仅服务 /api/demo/* 教学接口）。

四个教学状态共用一个代码版本和一个服务，教学故障被刻意隔离在本模块：

- Stage 1（null-failure）：一句话实现版本。空值不安全处理被保留在明确、
  局部、可读的位置，用于课堂稳定复现空姓名导致的导出失败；
- Stage 2（page-only）：空值与空结果已修复、文件合法，但导出错误地套用
  当前页分页，只导出当前页而不是全部筛选结果。

正式导出逻辑在 app/services/user_export_service.py，本模块不得影响它；
行格式与正式导出保持一致（空显示名称导出为空单元格），故障只在上述两处。
"""

import logging

from app.models.user import User, UserStatus
from app.services.user_export_service import USER_EXPORT_HEADERS
from app.services.user_service import UserService
from app.utils.excel import CellValue, build_excel, clean_text

logger = logging.getLogger("demo.export")


class DemoExportError(ValueError):
    """教学演示中可预期、可解释的导出失败。"""


def to_export_row(user: User) -> list[CellValue]:
    """与正式导出相同的行格式：空显示名称导出为空单元格。"""

    return [
        user.id,
        clean_text(user.username),
        clean_text(user.display_name or ""),
        clean_text(user.email),
        user.status.value,
        user.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    ]


class DemoExportService:
    def __init__(self, user_service: UserService) -> None:
        self._user_service = user_service

    def export_users_null_unsafe(
        self,
        *,
        username: str | None = None,
        status: UserStatus | None = None,
    ) -> bytes:
        """Stage 1 教学导出：一句话实现版本。

        空值不安全处理（刻意保留的教学故障）：实现时顺手加了一行“首条记录”
        日志，对可空的 display_name 直接调用 .strip()。默认导出首条是
        alice，侥幸成功；筛选结果首条为空姓名用户（如 bob）时稳定失败。
        空结果同样未定义：直接访问 users[0] 触发 IndexError。
        """

        users = self._user_service.search_users(username=username, status=status)

        first = None
        try:
            # —— 教学故障点：空结果与空值均未处理 ——
            first = users[0]
            logger.info(
                "[demo:null-failure] 导出 %d 条，首条用户：%s",
                len(users),
                first.display_name.strip(),
            )
        except IndexError as exc:
            logger.error("[demo:null-failure] 导出失败：结果为空，users[0] 触发 IndexError")
            raise DemoExportError(
                "空结果未处理：一句话实现直接访问首条记录，筛选结果为空时触发 IndexError"
            ) from exc
        except AttributeError as exc:
            logger.error(
                "[demo:null-failure] 导出失败：用户 %s 的显示名称为 None，.strip() 触发 AttributeError",
                first.username,
            )
            raise DemoExportError(
                f"空值处理错误：用户 {first.username} 的显示名称为 None，"
                "一句话实现对其直接调用 .strip() 触发 AttributeError"
            ) from exc

        rows = [to_export_row(user) for user in users]
        return build_excel(USER_EXPORT_HEADERS, rows, sheet_name="用户列表")

    def export_users_current_page(
        self,
        *,
        page: int,
        page_size: int,
        username: str | None = None,
        status: UserStatus | None = None,
    ) -> bytes:
        """Stage 2 教学导出：空值已修复、文件合法，但错误地只导出当前页。

        筛选口径与正式导出一致（复用 UserService.search_users），行格式一致；
        唯一的教学故障是这里对筛选结果套用了 page/page_size 分页。
        """

        matched = self._user_service.search_users(username=username, status=status)
        start = (page - 1) * page_size
        end = start + page_size
        rows = [to_export_row(user) for user in matched[start:end]]
        return build_excel(USER_EXPORT_HEADERS, rows, sheet_name="用户列表")
