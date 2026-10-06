from typing import Protocol

from ..models.camera_device import CameraDevice
from ..models.capture_configuration import CaptureConfiguration, CaptureProperties
from ..models.frame import Frame


class CameraPort(Protocol):
    def discover(self) -> list[CameraDevice]: ...

    def open(self, config: CaptureConfiguration) -> CaptureProperties: ...

    def read(self) -> Frame | None: ...

    def close(self) -> None: ...

    @property
    def is_open(self) -> bool: ...
