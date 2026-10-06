from dataclasses import dataclass
from enum import Enum


DISCOVERY_REQUEST = "BLANQUITA_VISION_DISCOVER".encode("utf-8")
DISCOVERY_RESPONSE = "BLANQUITA_VISION_HERE:8765".encode("utf-8")


class DiscoveryServiceState(Enum):
    STOPPED = "STOPPED"
    STARTING = "STARTING"
    LISTENING = "LISTENING"
    STOPPING = "STOPPING"
    ERROR = "ERROR"


@dataclass(frozen=True)
class DiscoveryStatus:
    state: DiscoveryServiceState
    bind_address: str
    udp_port: int
    websocket_advertisable: bool = False
    valid_requests_count: int = 0
    invalid_requests_count: int = 0
    responses_sent_count: int = 0
    send_errors_count: int = 0
    suppressed_requests_count: int = 0
    last_error: str | None = None
