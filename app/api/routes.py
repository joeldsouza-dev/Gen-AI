from fastapi import APIRouter, HTTPException, Request

from app.core.models import (
    GatewayRequest,
    ProviderError,
    RateLimitError,
)

router = APIRouter(
    prefix="/v1",
    tags=["Gateway"],
)


@router.post("/chat/completions")
async def chat_completions(
    gateway_request: GatewayRequest,
    request: Request,
):
    gateway_router = request.app.state.gateway_router
    

    try:
        response = await gateway_router.route_request(
            gateway_request
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

            raise HTTPException(
                status_code=500,
                detail=str(error),
            )


@router.get("/health")
async def health():
    return {
        "status": "ok",
    }