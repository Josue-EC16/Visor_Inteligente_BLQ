from typing import Protocol

from ..models.detection import Detection, DetectionParameters
from ..models.frame import Frame


class DetectorPort(Protocol):
    def detect(self, frame: Frame, parameters: DetectionParameters) -> Detection: ...
