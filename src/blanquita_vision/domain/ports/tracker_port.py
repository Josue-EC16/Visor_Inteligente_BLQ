from typing import Protocol

from ..models.frame import Frame
from ..models.geometry import BoundingBox
from ..models.tracking import TrackingResult


class TrackerPort(Protocol):
    def initialize(self, frame: Frame, box: BoundingBox) -> None: ...

    def update(self, frame: Frame) -> TrackingResult: ...

    def reset(self) -> None: ...
