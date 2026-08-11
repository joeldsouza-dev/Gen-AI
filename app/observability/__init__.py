from app.observability.emitter import EventEmitter
from app.observability.events import GatewayEvent
from app.observability.handlers import (
    log_event,
    record_metric,
)

event_emitter = EventEmitter()

event_emitter.subscribe(
    GatewayEvent,
    log_event,
)

event_emitter.subscribe(
    GatewayEvent,
    record_metric,
)