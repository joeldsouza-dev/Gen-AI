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


@app.on_event("startup")
async def startup() -> None:
    app.state.gateway_router = create_gateway_router()