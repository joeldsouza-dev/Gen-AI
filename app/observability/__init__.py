from app.observability.emitter import EventEmitter
from app.observability.events import GatewayEvent
from app.observability.handlers import log_event

event_emitter = EventEmitter()

# Register the logger as the first subscriber.
event_emitter.subscribe(
    GatewayEvent,
    log_event,
)