from threading import Event
from typing import Callable

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot

from ...application.camera_session import CameraEvent, CameraSession
from ...application.latest_frame_store import LatestFrameStore
from ...application.recovery_policy import RecoveryPolicy
from ...domain.models.capture_configuration import CaptureConfiguration
from ...domain.ports.camera_port import CameraPort


class CameraWorker(QThread):
    event = Signal(object)

    def __init__(self, session: CameraSession, action: str,
                 config: CaptureConfiguration | None, parent=None) -> None:
        super().__init__(parent)
        self.session = session
        self.action = action
        self.config = config

    def run(self) -> None:
        self.session.execute(self.action, self.config)


class QtCameraRunner(QObject):
    idle = Signal()

    def __init__(self, camera_factory: Callable[[Event], CameraPort],
                 store: LatestFrameStore,
                 policy: RecoveryPolicy = RecoveryPolicy(), parent=None) -> None:
        super().__init__(parent)
        self._factory = camera_factory
        self._store = store
        self._policy = policy
        self._worker: CameraWorker | None = None
        self._cancel = Event()
        self._event_handler: Callable = lambda event: None
        self._finished_handler: Callable = lambda: None

    @property
    def active(self) -> bool:
        # Continúa activo hasta procesar finished en el hilo principal.
        return self._worker is not None

    def bind(self, event_handler: Callable, finished_handler: Callable) -> None:
        self._event_handler = event_handler
        self._finished_handler = finished_handler

    def start(self, action: str, config: CaptureConfiguration | None) -> None:
        if self.active:
            raise RuntimeError("Ya existe una operación de cámara activa.")
        self._cancel = Event()
        camera = self._factory(self._cancel)
        worker = CameraWorker(
            CameraSession(camera, self._store, self._cancel, self._emit,
                          self._policy), action, config, self,
        )
        self._worker = worker
        worker.event.connect(self._receive)
        worker.finished.connect(self._finished)
        worker.start()

    def _emit(self, event: CameraEvent) -> None:
        worker = self._worker
        if worker is not None:
            worker.event.emit(event)

    @Slot(object)
    def _receive(self, event: CameraEvent) -> None:
        self._event_handler(event)

    @Slot()
    def _finished(self) -> None:
        worker = self._worker
        if worker is None:
            return
        # finished puede preceder a la limpieza interna final del hilo.
        if not worker.wait(0):
            QTimer.singleShot(0, self._finished)
            return
        self._worker = None
        worker.deleteLater()
        self._finished_handler()
        self.idle.emit()

    def cancel(self) -> None:
        self._cancel.set()
