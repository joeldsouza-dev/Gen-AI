from collections import defaultdict
from typing import Callable

from app.observability.events import GatewayEvent


class EventEmitter:
    """
    Simple in-memory publish/subscribe event bus.

    Components emit events.
    Other components subscribe and react independently.
    """

    def __init__(self):
        # Dictionary:
        # Event Type -> List of Handlers
        self._subscribers: dict[type, list[Callable[[GatewayEvent], None]]] = defaultdict(list)

    def subscribe(
        self,
        event_type: type[GatewayEvent],
        handler: Callable[[GatewayEvent], None],
    ) -> None:
        """
        Register a handler for a specific event type.
        """
        self._subscribers[event_type].append(handler)

    def emit(self, event: GatewayEvent) -> None:
        """
        Notify all handlers that are interested in this event.

        Using isinstance() allows handlers subscribed to GatewayEvent
        to receive ALL events derived from GatewayEvent.
        """
        for subscribed_type, handlers in self._subscribers.items():

            if isinstance(event, subscribed_type):

                for handler in handlers:
                    handler(event)