from datetime import datetime

from app.observability import event_emitter
from app.observability.events import RequestStartedEvent


event = RequestStartedEvent(
    request_id="demo-123",
    timestamp=datetime.now(),
    event_type="request_started",
    team_id="team-1",
)

event_emitter.emit(event)