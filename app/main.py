from fastapi import FastAPI

from app.api import routes
from app.bootstrap import create_gateway_router
from app.middleware.request_id import RequestIDMiddleware

app = FastAPI(
    title="LLM Gateway",
    version="1.0.0",
)

app.add_middleware(RequestIDMiddleware)

app.include_router(routes.router)

# Root-level metrics & health for Prometheus scrapers
app.add_api_route("/metrics", routes.get_metrics, methods=["GET"])
app.add_api_route("/health", routes.health, methods=["GET"])


@app.on_event("startup")
async def startup() -> None:
    app.state.gateway_router = create_gateway_router()