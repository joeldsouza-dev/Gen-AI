from app.observability.events import GatewayEvent
from app.observability.logger import logger


def log_event(event: GatewayEvent) -> None:
    """
    Default logging handler.

    Every emitted GatewayEvent passes through here.
    """
    logger.info(event)