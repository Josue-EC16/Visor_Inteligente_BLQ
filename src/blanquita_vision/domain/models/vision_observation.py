from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from .calibration import CalibrationStatus
from .detection import Detection, DetectionState
from .position import PositionEstimate, PositionStatus
from .tracking import TrackingResult


class VisionPipelineState(Enum):
    STOPPED = "STOPPED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    ERROR = "ERROR"


@dataclass(frozen=True)
class VisionObservation:
    frame_sequence: int
    timestamp: datetime
    detection: Detection | None
    tracking: TrackingResult | None
    position: PositionEstimate | None
    calibration_status: CalibrationStatus
    pipeline_state: VisionPipelineState
    processing_time_ms: float | None = None
    detection_state: DetectionState = DetectionState.SEARCHING
    position_status: PositionStatus = PositionStatus.UNAVAILABLE
