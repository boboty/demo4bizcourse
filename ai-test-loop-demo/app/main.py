from fastapi import FastAPI

from app.models import OrderCalculateRequest, OrderCalculateResponse
from app.service import calculate_order


def create_app() -> FastAPI:
    app = FastAPI(title="AgentAI Test Demo - Order Calculate", version="1.0.0")

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/orders/calculate", response_model=OrderCalculateResponse, tags=["orders"])
    def order_calculate(order: OrderCalculateRequest) -> OrderCalculateResponse:
        return calculate_order(order)

    return app


app = create_app()
