import logging
from dataclasses import dataclass, replace
from threading import Event
from typing import Callable

from ..domain.models.camera_state import CameraError, CameraState
from ..domain.models.capture_configuration import CaptureConfiguration
from ..domain.models.frame import Frame
from ..domain.ports.camera_port import CameraPort
from .latest_frame_store import LatestFrameStore
from .recovery_policy import RecoveryPolicy

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CameraEvent:
    kind: str
    value: object = None


class CameraSession:
    """Operaciones bloqueantes; se ejecuta íntegramente en un único worker."""

    def __init__(
        self, camera: CameraPort, store: LatestFrameStore,
        cancellation: Event, emit: Callable[[CameraEvent], None],
        policy: RecoveryPolicy = RecoveryPolicy(),
    ) -> None:
        self.camera = camera
        self.store = store
        self.cancellation = cancellation
        self.emit = emit
        self.policy = policy

    def _state(self, state: CameraState) -> None:
        if not self.cancellation.is_set():
            self.emit(CameraEvent("state", state))

    def _close(self) -> None:
        try:
            self.camera.close()
        except Exception:
            logger.warning("camera_release_failed", exc_info=True)

    def execute(self, action: str, config: CaptureConfiguration | None) -> None:
        try:
            if action == "discover":
                logger.info("camera_discovery_started")
                devices = self.camera.discover()
                if not self.cancellation.is_set():
                    self.emit(CameraEvent("devices", devices))
                    self._state(CameraState.DISCONNECTED)
                    logger.info("camera_discovery_completed count=%s", len(devices))
            elif action == "connect" and config is not None:
                self._stream(config)
            else:
                raise CameraError("invalid_action", "Operación de cámara inválida.")
        except Exception as exc:
            if not self.cancellation.is_set():
                error = exc if isinstance(exc, CameraError) else CameraError(
                    "worker_failed", "Error inesperado en el worker de cámara.",
                )
                logger.error("camera_error code=%s", error.code, exc_info=True)
                self.emit(CameraEvent("error", error))
        finally:
            self._close()
            self.store.end_capture()

    def _open_valid(self, config: CaptureConfiguration) -> Frame:
        properties = self.camera.open(config)
        if self.cancellation.is_set():
            raise CameraError("cancelled", "Operación cancelada.")
        frame = self.camera.read()
        if frame is None:
            self.store.record_invalid()
            raise CameraError("first_frame_invalid", "La cámara no entregó un primer frame válido.")
        if self.cancellation.is_set():
            raise CameraError("cancelled", "Operación cancelada.")
        # La imagen recibida es la autoridad sobre la resolución efectiva.
        properties = replace(properties, width=frame.width, height=frame.height)
        self.emit(CameraEvent("properties", properties))
        return frame

    def _publish(self, frame: Frame) -> None:
        if not self.cancellation.is_set() and self.store.publish(frame):
            self.emit(CameraEvent("frame"))

    def _recover(self, config: CaptureConfiguration) -> Frame | None:
        logger.warning("camera_lost")
        self.store.clear()
        self._state(CameraState.RECOVERING)
        self._close()
        logger.info("camera_recovery_started")
        for attempt in range(self.policy.attempts):
            if self.cancellation.wait(self.policy.interval_seconds):
                return None
            self.store.record_reconnect()
            try:
                frame = self._open_valid(config)
                self._state(CameraState.STREAMING)
                logger.info("camera_recovery_succeeded attempt=%s", attempt + 1)
                return frame
            except Exception:
                self._close()
                if self.cancellation.is_set():
                    return None
                logger.warning("camera_recovery_attempt_failed attempt=%s",
                               attempt + 1, exc_info=True)
        logger.error("camera_recovery_exhausted")
        raise CameraError("recovery_exhausted",
                          "Recuperación agotada. Comprueba la cámara y pulsa Reintentar.")

    def _stream(self, config: CaptureConfiguration) -> None:
        logger.info("camera_connecting index=%s", config.device_index)
        frame = self._open_valid(config)
        self.store.begin_capture()
        self._state(CameraState.STREAMING)
        logger.info("camera_connected")
        self._publish(frame)
        failures = 0
        while not self.cancellation.is_set():
            frame = self.camera.read()
            if self.cancellation.is_set():
                return
            if frame is None:
                failures += 1
                self.store.record_invalid()
                logger.warning("camera_invalid_frame consecutive=%s", failures)
                if failures < self.policy.invalid_read_limit:
                    continue
                frame = self._recover(config)
                if frame is None:
                    return
            failures = 0
            self._publish(frame)
