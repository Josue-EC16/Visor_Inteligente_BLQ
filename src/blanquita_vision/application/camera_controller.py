import logging
from dataclasses import replace
from typing import Callable, Protocol

from ..domain.models.camera_device import CameraDevice
from ..domain.models.camera_state import CameraError, CameraRuntimeState, CameraState
from ..domain.models.capture_configuration import CaptureConfiguration
from ..domain.models.frame import CapturedFrame, Frame
from .camera_session import CameraEvent
from .latest_frame_store import LatestFrameStore

logger = logging.getLogger(__name__)


class CameraRunner(Protocol):
    @property
    def active(self) -> bool: ...

    def start(self, action: str, config: CaptureConfiguration | None) -> None: ...

    def cancel(self) -> None: ...

    def bind(self, event_handler: Callable, finished_handler: Callable) -> None: ...


class CameraController:
    """Estado coordinado en el hilo de presentación; sin dependencias Qt/cv2."""

    def __init__(self, runner: CameraRunner, store: LatestFrameStore,
                 backend: str = "AUTO") -> None:
        self.runner = runner
        self.store = store
        self.backend = backend
        self.runtime = CameraRuntimeState()
        self.devices: list[CameraDevice] = []
        self.on_state: list[Callable[[CameraRuntimeState], None]] = []
        self.on_frame: list[Callable[[Frame], None]] = []
        self.on_devices: list[Callable[[list[CameraDevice]], None]] = []
        self._stopping = False
        runner.bind(self.handle_event, self.operation_finished)

    def _update(self, **changes) -> None:
        self.runtime = replace(self.runtime, **changes)
        for callback in self.on_state:
            callback(self.runtime)

    def select(self, device_id: str | None) -> None:
        if self.runner.active or self.runtime.state not in (
            CameraState.DISCONNECTED, CameraState.ERROR,
        ):
            return
        device = next((item for item in self.devices if item.id == device_id), None)
        if device_id is None:
            self._update(selected_device=None)
        elif device is not None:
            logger.info("camera_selected index=%s", device.index)
            self._update(selected_device=device)

    def refresh(self) -> None:
        if self.runner.active or self.runtime.state not in (
            CameraState.DISCONNECTED, CameraState.ERROR,
        ):
            return
        self._stopping = False
        self.store.clear()
        self._update(state=CameraState.DISCOVERING, properties=None,
                     last_error=None, last_frame_at=None)
        self.runner.start("discover", None)
        self._update()

    def connect(self) -> None:
        device = self.runtime.selected_device
        if self.runner.active or device is None or self.runtime.state not in (
            CameraState.DISCONNECTED, CameraState.ERROR,
        ):
            return
        self._stopping = False
        self.store.clear()
        self._update(state=CameraState.CONNECTING, properties=None,
                     last_error=None, last_frame_at=None)
        self.runner.start("connect", CaptureConfiguration(device.index, self.backend))
        self._update()

    def disconnect(self) -> None:
        if self.runner.active:
            self._stopping = True
            self._update(state=CameraState.STOPPING)
            self.runner.cancel()
        else:
            self._clear_session()
        logger.info("camera_disconnected_by_user")

    def _clear_session(self) -> None:
        self.store.clear()
        self._update(state=CameraState.DISCONNECTED, properties=None,
                     last_frame_at=None, last_error=None)

    def operation_finished(self) -> None:
        if self._stopping:
            self._stopping = False
            self._clear_session()
        else:
            self._update()

    def handle_event(self, event: CameraEvent) -> None:
        if self._stopping:
            return
        if event.kind == "devices":
            self.devices = event.value
            previous = self.runtime.selected_device
            selected = next((d for d in self.devices if previous and d.id == previous.id), None)
            self._update(selected_device=selected)
            for callback in self.on_devices:
                callback(self.devices)
        elif event.kind == "properties":
            self._update(properties=event.value)
        elif event.kind == "state":
            changes = {"state": event.value}
            if event.value is CameraState.RECOVERING:
                changes.update(properties=None, last_frame_at=None)
            self._update(**changes)
        elif event.kind == "error":
            self.store.clear()
            self._update(state=CameraState.ERROR, last_error=event.value,
                         properties=None, last_frame_at=None)
        elif event.kind == "frame":
            frame = self.store.consume()
            if frame is not None and self.runtime.state is CameraState.STREAMING:
                self._update(last_frame_at=frame.captured_at)
                for callback in self.on_frame:
                    callback(frame)

    def capture(self) -> CapturedFrame:
        if self.runtime.state is not CameraState.STREAMING:
            raise CameraError("snapshot_unavailable", "No hay un frame actual disponible.")
        captured = self.store.snapshot()
        if captured is None:
            raise CameraError("snapshot_unavailable", "No hay un frame válido disponible.")
        return captured
