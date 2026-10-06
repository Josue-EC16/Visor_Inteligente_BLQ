from PySide6.QtCore import QObject, QTimer, Signal


class QtOperationsController(QObject):
    changed = Signal()

    def __init__(self, service, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self._relay = self.changed.emit
        service.on_change.append(self._relay)
        self.timer = QTimer(self)
        self.timer.setInterval(200)
        self.timer.timeout.connect(service.tick)

    def start(self) -> None:
        self.service.storage.start()
        self.service.network.start()
        self.timer.start()

    @property
    def active(self) -> bool:
        return self.service.storage.active or self.service.network.active

    def shutdown(self) -> None:
        self.timer.stop()
        self.service.begin_shutdown()

    def finish_storage(self) -> None:
        if not self.service.network.active:
            self.service.drain_network_events()
            self.service.storage.shutdown()

    def dispose(self) -> None:
        self.timer.stop()
        self.service.dispose()
        if self._relay in self.service.on_change:
            self.service.on_change.remove(self._relay)
