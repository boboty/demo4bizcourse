from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.api.users import router as users_router
from app.repositories.user_repository import InMemoryUserRepository
from app.services.user_export_service import UserExportService
from app.services.user_service import UserService

STATIC_DIR = Path(__file__).resolve().parent / "static"


def create_app(repository: InMemoryUserRepository | None = None) -> FastAPI:
    app = FastAPI(title="AI 研发课程演示 API", version="0.1.0")
    user_repository = repository or InMemoryUserRepository.with_sample_data()
    user_service = UserService(user_repository)
    app.state.user_service = user_service
    app.state.user_export_service = UserExportService(user_service)
    app.include_router(users_router)

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/demo/users", include_in_schema=False)
    def demo_users_page() -> FileResponse:
        """课堂演示用用户列表页面（静态单文件，无外部依赖）。"""

        return FileResponse(STATIC_DIR / "demo_users.html")

    return app


app = create_app()
