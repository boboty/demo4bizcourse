from fastapi import FastAPI

from app.models import DiscountPreviewRequest, DiscountPreviewResponse
from app.service import preview_discount


def create_app() -> FastAPI:
    app = FastAPI(title="AI Test Loop - Discount Preview", version="1.0.0")

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post(
        "/api/orders/discount-preview",
        response_model=DiscountPreviewResponse,
        tags=["orders"],
    )
    def discount_preview(order: DiscountPreviewRequest) -> DiscountPreviewResponse:
        return preview_discount(order)

    return app


app = create_app()

