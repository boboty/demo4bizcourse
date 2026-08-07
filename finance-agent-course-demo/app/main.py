from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
SCENARIO_PAGES = {
    "knowledge-answer": "knowledge-answer.html",
    "batch-workflow": "batch-workflow.html",
    "exception-agent": "exception-agent.html",
    "independent-validation": "independent-validation.html",
    "month-close": "month-close.html",
}


def create_app() -> FastAPI:
    app = FastAPI(title="企业 AI 大模型与智能体课程财务演示套件", version="1.0.0")
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        return RedirectResponse(url="/demo")

    @app.get("/demo", include_in_schema=False)
    def overview() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/demo/{scenario}", include_in_schema=False)
    def scenario(scenario: str) -> FileResponse:
        filename = SCENARIO_PAGES.get(scenario)
        if filename is None:
            raise HTTPException(status_code=404, detail=f"未知演示：{scenario}")
        return FileResponse(STATIC_DIR / "scenarios" / filename)

    return app


app = create_app()

