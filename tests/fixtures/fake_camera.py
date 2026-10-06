from collections import deque
from datetime import datetime, timezone
from threading import Event

import numpy as np

from blanquita_vision.domain.models.camera_device import CameraDevice
from blanquita_vision.domain.models.camera_state import CameraError
from blanquita_vision.domain.models.capture_configuration import CaptureProperties
from blanquita_vision.domain.models.frame import Frame


def make_frame(sequence: int = 0) -> Frame:
    image = np.full((12, 16, 3), sequence % 256, dtype=np.uint8)
    return Frame(sequence, datetime.now(timezone.utc), 16, 12, image)


class FakeCamera:
    """Escenarios deterministas sin hardware; sustituye CameraPort."""

    def __init__(self, indices=(0, 2), open_errors=(), reads=(),
                 delay=0.005, cancellation=None) -> None:
        self.devices = [CameraDevice(str(i), i, f"Cámara {i}") for i in indices]
        self.open_errors = deque(open_errors)
        self.reads = deque(reads)
        self.delay = delay
        self.cancellation = cancellation or Event()
        self.open_calls = []
        self.close_calls = 0
        self.read_calls = 0
        self.discovery_calls = 0
        self._open = False
        self._sequence = 0
        self.owner_threads = []

    def _record_thread(self) -> None:
        from threading import get_ident
        self.owner_threads.append(get_ident())

    def discover(self):
        self._record_thread()
        self.discovery_calls += 1
        return self.devices.copy()

    def open(self, config):
        self._record_thread()
        self.open_calls.append(config)
        if self.open_errors:
            error = self.open_errors.popleft()
            if error is not None:
                raise error
        self._open = True
        return CaptureProperties(16, 12, 25.0, "FAKE")

    def read(self):
        self._record_thread()
        self.read_calls += 1
        if self.cancellation.wait(self.delay) or not self._open:
            return None
        if self.reads:
            result = self.reads.popleft()
            if isinstance(result, Exception):
                raise result
            return result
        frame = make_frame(self._sequence)
        self._sequence += 1
        return frame

    def close(self):
        self._record_thread()
        self.close_calls += 1
        self._open = False

    @property
    def is_open(self):
        return self._open
