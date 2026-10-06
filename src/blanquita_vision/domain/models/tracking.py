from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from .geometry import BoundingBox, ImagePoint


class TrackingState(Enum):
    INACTIVE = "INACTIVE"
    INITIALIZING = "INITIALIZING"
    TRACKING = "TRACKING"
    LOST = "LOST"
    ERROR = "ERROR"


@dataclass(frozen=True)
class TrackingResult:
    state: TrackingState
    bounding_box: BoundingBox | None
    centroid: ImagePoint | None
    source: str
    timestamp: datetime
