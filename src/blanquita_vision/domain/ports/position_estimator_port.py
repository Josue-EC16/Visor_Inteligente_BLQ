from typing import Protocol

from ..models.calibration import Calibration
from ..models.geometry import ImagePoint
from ..models.position import SpatialPosition


class PositionEstimatorPort(Protocol):
    def estimate(self, image_point: ImagePoint, calibration: Calibration) -> SpatialPosition: ...
