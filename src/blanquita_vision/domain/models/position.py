from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from math import isfinite


class PositionStatus(Enum):
    UNAVAILABLE = "UNAVAILABLE"
    RAW_AVAILABLE = "RAW_AVAILABLE"
    FILTERED_AVAILABLE = "FILTERED_AVAILABLE"
    INVALID = "INVALID"


@dataclass(frozen=True)
class SpatialPosition:
    x: float | None = None
    y: float | None = None
    z: float | None = None
    unit: str | None = None

    def __post_init__(self) -> None:
        if any(v is not None and not isfinite(v) for v in (self.x, self.y, self.z)):
            raise ValueError("Posición no finita.")


@dataclass(frozen=True)
class PositionEstimate:
    raw_position: SpatialPosition
    filtered_position: SpatialPosition
    confidence: float
    timestamp: datetime
    angle: float | None = None
    calibrated: bool = False


@dataclass
class EmaFilterState:
    alpha: float
    initialized: bool = False
    last_x: float | None = None
    last_y: float | None = None
