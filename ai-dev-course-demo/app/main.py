from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse

from app.api.demo import router as demo_router
from app.api.users import router as users_router
from app.repositories.user_repository import InMemoryUserRepository
from app.services.demo_export_service import DemoExportService
from app.services.user_export_service import UserExportService
from app.services.user_service import UserService

STATIC_DIR = Path(__file__).resolve().parent / "static"

# 课堂演示四个状态页，共用同一个静态页面，由受控路由决定状态；未知状态 404。
DEMO_PAGE_STATES = ("base", "null-failure", "page-only", "final")


def create_app(repository: InMemoryUserRepository | None = None) -> FastAPI:
    app = FastAPI(title="AI 研发课程演示 API", version="0.1.0")
    user_repository = repository or InMemoryUserRepository.with_sample_data()
    user_service = UserService(user_repository)
    app.state.user_service = user_service
    app.state.user_export_service = UserExportService(user_service)
    app.state.demo_export_service = DemoExportService(user_service)
    app.include_router(users_router)
    app.include_router(demo_router)

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/", include_in_schema=False)
    def root_page() -> RedirectResponse:
        """根路径重定向到课堂演示导航页，避免课堂现场手动敲 /demo。"""

        return RedirectResponse(url="/demo")

    @app.get("/demo", include_in_schema=False)
    def demo_nav_page() -> FileResponse:
        """课堂演示导航页（静态单文件，无外部依赖）。"""

        return FileResponse(STATIC_DIR / "demo_nav.html")

    @app.get("/demo/users", include_in_schema=False)
    def demo_users_page() -> RedirectResponse:
        """旧入口保持兼容：重定向到最终状态页。"""

        return RedirectResponse(url="/demo/users/final")

    @app.get("/demo/users/{state}", include_in_schema=False)
    def demo_users_state_page(state: str) -> FileResponse:
        """课堂演示状态页（四个状态共用同一静态页面，无外部依赖）。"""

        if state not in DEMO_PAGE_STATES:
            raise HTTPException(status_code=404, detail=f"未知演示状态：{state}")
        return FileResponse(STATIC_DIR / "demo_users.html")

    @app.get("/demo/codex-loop", include_in_schema=False)
    def demo_codex_loop_page() -> FileResponse:
        """Demo 2：完整任务包驱动研发闭环（静态单文件模拟，不调用任何模型接口）。"""

        return FileResponse(STATIC_DIR / "demo_codex_loop.html")

    return app


app = create_app()
