from threading import Lock

from .vision_pipeline import ProcessedFrame


class LatestObservationStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._result: ProcessedFrame | None = None
        self._pending = False

    def publish(self, result: ProcessedFrame) -> bool:
        with self._lock:
            notify = not self._pending
            self._result = result
            self._pending = True
            return notify

    def consume(self) -> ProcessedFrame | None:
        with self._lock:
            self._pending = False
            return self._result

    def clear(self) -> None:
        with self._lock:
            self._result = None
            self._pending = False
