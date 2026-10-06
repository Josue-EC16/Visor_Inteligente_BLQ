import asyncio

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot


class NetworkWorker(QThread):
    def __init__(self, server, parent=None) -> None:
        super().__init__(parent)
        self.server = server

    def run(self) -> None:
        asyncio.run(self.server.run())


class QtNetworkController(QObject):
    idle = Signal()

    def __init__(self, server, parent=None) -> None:
        super().__init__(parent)
        self.server = server
        self._worker = NetworkWorker(server, self)
        self._worker.finished.connect(self._finished)
        self._started = False

    @property
    def active(self) -> bool:
        return self._started and self._worker is not None

    def start(self) -> None:
        self._started = True
        self._worker.start()

    def shutdown(self) -> None:
        self.server.request_stop()

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
