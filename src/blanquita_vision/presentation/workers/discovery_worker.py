import asyncio

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot

from ...domain.models.discovery import DiscoveryStatus


class DiscoveryWorker(QThread):
    def __init__(self, responder, parent=None) -> None:
        super().__init__(parent)
        self.responder = responder

    def run(self) -> None:
        asyncio.run(self.responder.run())


class QtDiscoveryController(QObject):
    """Fachada DiscoveryResponderPort; el socket pertenece al adapter/worker."""

    idle = Signal()

    def __init__(self, responder, parent=None) -> None:
        super().__init__(parent)
        self.responder = responder
        self._worker = DiscoveryWorker(responder, self)
        self._worker.finished.connect(self._finished)
        self._started = False

    @property
    def active(self) -> bool:
        return self._started and self._worker is not None

    def start(self) -> None:
        if self._started or self._worker is None:
            return
        self._started = True
        self._worker.start()

    def stop(self) -> None:
        self.responder.request_stop()

    def snapshot(self) -> DiscoveryStatus:
        return self.responder.snapshot()

    @Slot()
    def _finished(self) -> None:
        if self._worker is None:
            return
        if not self._worker.wait(0):
            QTimer.singleShot(0, self._finished)
            return
        self._worker.deleteLater()
        self._worker = None
        self.idle.emit()
