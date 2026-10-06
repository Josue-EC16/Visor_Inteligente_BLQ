from dataclasses import dataclass
from threading import Condition, Event, Lock
from time import monotonic

from ..domain.models.frame import CapturedFrame, Frame


@dataclass(frozen=True)
class CaptureMetrics:
    frames_captured: int
    invalid_frames: int
    stale_frames_replaced: int
    reconnect_attempts: int
    measured_fps: float | None


class LatestFrameStore:
    """Un frame vigente; nunca se encola una imagen en las señales de Qt."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._condition = Condition(self._lock)
        self._revision = 0
        self._frame: Frame | None = None
        self._pending = False
        self.frames_captured = 0
        self.stale_frames_replaced = 0
        self._invalid_frames = 0
        self._reconnect_attempts = 0
        self._started_at: float | None = None
        self._stopped_at: float | None = None
        self._initial_count = 0

    def begin_capture(self) -> None:
        with self._lock:
            self._started_at = monotonic()
            self._stopped_at = None
            self._initial_count = self.frames_captured

    def end_capture(self) -> None:
        with self._lock:
            self._stopped_at = monotonic()

    def record_invalid(self) -> None:
        with self._lock:
            self._invalid_frames += 1

    def record_reconnect(self) -> None:
        with self._lock:
            self._reconnect_attempts += 1

    def publish(self, frame: Frame) -> bool:
        """Devuelve True solo cuando hace falta una nueva notificación."""
        with self._lock:
            if self._pending:
                self.stale_frames_replaced += 1
            notify = not self._pending
            self._frame = frame
            self._pending = True
            self.frames_captured += 1
            self._revision += 1
            self._condition.notify_all()
            return notify

    def latest(self) -> Frame | None:
        with self._lock:
            return self._frame

    def consume(self) -> Frame | None:
        with self._lock:
            self._pending = False
            return self._frame

    def wait_next(self, revision: int, cancellation: Event) -> tuple[int, Frame | None]:
        """Cursor independiente: consumir en UI no afecta al Vision Worker."""
        with self._condition:
            self._condition.wait_for(lambda: self._revision != revision or cancellation.is_set())
            return self._revision, None if cancellation.is_set() else self._frame

    def wake_consumers(self) -> None:
        with self._condition:
            self._condition.notify_all()

    def snapshot(self) -> CapturedFrame | None:
        with self._lock:
            frame = self._frame
        if frame is None:
            return None
        # Los adapters publican imágenes propias, sin reutilizar su memoria.
        return CapturedFrame(frame.sequence, frame.captured_at, frame.image.copy())

    def clear(self) -> None:
        with self._lock:
            self._frame = None
            self._pending = False
            self._revision += 1
            self._condition.notify_all()

    def metrics(self) -> CaptureMetrics:
        with self._lock:
            fps = None
            if self._started_at is not None:
                elapsed = (self._stopped_at or monotonic()) - self._started_at
                if elapsed > 0:
                    fps = (self.frames_captured - self._initial_count) / elapsed
            return CaptureMetrics(
                self.frames_captured, self._invalid_frames,
                self.stale_frames_replaced, self._reconnect_attempts, fps,
            )
