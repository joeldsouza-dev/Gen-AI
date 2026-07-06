"""
HTTP layer. This file is basically done for you — it's a thin wrapper that
validates input (via Pydantic, automatically) and calls the router. The
interesting work already happened in router.py / rate_limiter.py /
circuit_breaker.py / the provider files.

Once those are implemented, this endpoint should Just Work:
    POST /v1/completions
    { "team_id": "demo", "prompt": "Say hello in one sentence." }
"""

from fastapi import APIRouter, HTTPException

from app.core.models import GatewayRequest, GatewayResponse
from app.core.router import GatewayRouter

router = APIRouter()

# NOTE: this module-level singleton is intentionally simple for now.
# Once app/main.py wires up real providers/limiters/breakers, this should
# be replaced with a properly constructed GatewayRouter instance (e.g. via
# FastAPI's dependency injection, or a simple app.state attachment in main.py).
gateway_router: GatewayRouter | None = None


@router.post("/v1/completions", response_model=GatewayResponse)
async def create_completion(request: GatewayRequest) -> GatewayResponse:
    if gateway_router is None:
        raise HTTPException(status_code=503, detail="Gateway not yet wired up — see app/main.py")
    try:
        return await gateway_router.route_request(request)
    except NotImplementedError as e:
        # Friendly error while you're still building this out, instead of a
        # bare 500. Remove this except block once everything's implemented.
        raise HTTPException(status_code=501, detail=f"Not implemented yet: {e}")


@router.get("/v1/health")
async def health() -> dict:
    return {"status": "ok"}
