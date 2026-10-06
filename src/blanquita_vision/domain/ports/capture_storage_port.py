from typing import Protocol

from ..models.frame import CapturedFrame


class CaptureStoragePort(Protocol):
    def save_capture(self, capture: CapturedFrame, format: str) -> dict: ...
