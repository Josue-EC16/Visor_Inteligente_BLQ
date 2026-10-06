from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from .camera_device import CameraDevice
from .capture_configuration import CaptureProperties


class CameraState(Enum):
    DISCONNECTED = "DISCONNECTED"
    DISCOVERING = "DISCOVERING"
    CONNECTING = "CONNECTING"
    STREAMING = "STREAMING"
    RECOVERING = "RECOVERING"
    ERROR = "ERROR"
    STOPPING = "STOPPING"


@dataclass(frozen=True)
class CameraError(Exception):
    code: str
    message: str

    def __str__(self) -> str:
        return self.message


@dataclass(frozen=True)
class CameraRuntimeState:
    state: CameraState = CameraState.DISCONNECTED
    selected_device: CameraDevice | None = None
    properties: CaptureProperties | None = None
    last_frame_at: datetime | None = None
    last_error: CameraError | None = None

    @property
    def recovering(self) -> bool:
        return self.state is CameraState.RECOVERING
