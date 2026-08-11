from dataclasses import dataclass
from datetime import datetime


@dataclass
class GatewayEvent:
    request_id: str
    timestamp: datetime
    event_type: str

@dataclass
class RequestStartedEvent(GatewayEvent):
    team_id: str

@dataclass
class ProviderAttemptEvent(GatewayEvent):
    provider: str
    attempt: int

@dataclass
class ProviderSuccessEvent(GatewayEvent):
    provider: str
    latency_ms: float
    input_tokens: int
    output_tokens: int

@dataclass
class ProviderFailureEvent(GatewayEvent):
    provider: str
    error: str

@dataclass
class RetryEvent(GatewayEvent):
    provider: str
    attempt: int


@dataclass
class FallbackEvent(GatewayEvent):
    from_provider: str
    to_provider: str

@dataclass
class RequestFinishedEvent(GatewayEvent):
    provider: str
    total_latency_ms: float