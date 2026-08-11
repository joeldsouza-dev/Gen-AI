import time
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request

from app.core.models import (
    GatewayRequest,
    ProviderError,
    RateLimitError,
)
from app.observability import event_emitter
from app.observability.events import (
    RequestFinishedEvent,
    RequestStartedEvent,
)
from app.observability.handlers import metrics
router = APIRouter(
    prefix="/v1",
    tags=["Gateway"],
)


@router.post("/chat/completions")
async def chat_completions(
    gateway_request: GatewayRequest,
    request: Request,
):
    request_id = request.state.request_id
    start_time = time.perf_counter()

    event_emitter.emit(
        RequestStartedEvent(
            request_id=request_id,
            timestamp=datetime.now(),
            event_type="request_started",
            team_id=gateway_request.team_id,
        )
    )

    gateway_router = request.app.state.gateway_router

    try:
        response = await gateway_router.route_request(
            gateway_request,
            request_id,
        )

        total_latency_ms = (
            time.perf_counter() - start_time
        ) * 1000

        event_emitter.emit(
            RequestFinishedEvent(
                request_id=request_id,
                timestamp=datetime.now(),
                event_type="request_finished",
                provider=response.provider_used.value,
                total_latency_ms=total_latency_ms,
            )
        )

        return response

    except RateLimitError as error:
        raise HTTPException(
            status_code=429,
            detail=str(error),
        )

    except ProviderError as error:
        raise HTTPException(
            status_code=502,
            detail=str(error),
        )

    except Exception as error:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(error))

@router.get("/metrics")
async def get_metrics():
    return metrics.snapshot()

@router.get("/health")
async def health():
    return {
        "status": "ok",
    }
