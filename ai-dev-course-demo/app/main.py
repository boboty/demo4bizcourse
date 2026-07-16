from fastapi import FastAPI

from app.api.users import router as users_router
from app.repositories.user_repository import InMemoryUserRepository
from app.services.user_service import UserService


def create_app(repository: InMemoryUserRepository | None = None) -> FastAPI:
    app = FastAPI(title="AI 研发课程演示 API", version="0.1.0")
    user_repository = repository or InMemoryUserRepository.with_sample_data()
    app.state.user_service = UserService(user_repository)
    app.include_router(users_router)

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()

