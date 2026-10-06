import logging
from threading import Event
from typing import Callable

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot

from ...application.latest_frame_store import LatestFrameStore
from ...application.latest_observation_store import LatestObservationStore
from ...application.vision_pipeline import VisionPipeline
from ...domain.models.calibration import Calibration, CalibrationStatus
from ...domain.models.detection import DetectionParameters

logger = logging.getLogger(__name__)


class VisionWorker(QThread):
    event = Signal(str, object)

    def __init__(self, store: LatestFrameStore, results: LatestObservationStore,
                 cancellation: Event, factory: Callable[[], VisionPipeline], parent=None) -> None:
        super().__init__(parent)
        self.store, self.results = store, results
        self.cancellation = cancellation
        self.factory = factory

    def run(self) -> None:
        pipeline = None
        try:
            pipeline = self.factory()
            self.event.emit("started", None)
            revision = -1
            skipped = 0
            while not self.cancellation.is_set():
                current, frame = self.store.wait_next(revision, self.cancellation)
                if self.cancellation.is_set():
                    break
                if revision >= 0:
                    skipped += max(0, current - revision - 1)
                revision = current
                if frame is None:
                    continue
                result = pipeline.process(frame, skipped)
                if not self.cancellation.is_set() and self.results.publish(result):
                    self.event.emit("result", None)
        except Exception as exc:
            if not self.cancellation.is_set():
                logger.error("vision_worker_failed", exc_info=True)
                self.results.clear()
                self.event.emit("error", str(exc))
        finally:
            if pipeline is not None:
                try:
                    pipeline.reset()
                except Exception:
                    logger.warning("vision_reset_failed", exc_info=True)


class QtVisionRunner(QObject):
    idle = Signal()

    def __init__(self, store: LatestFrameStore, detector_factory: Callable,
                 tracker_factory: Callable, estimator_factory: Callable, parent=None) -> None:
        super().__init__(parent)
        self.store = store
        self.detector_factory = detector_factory
        self.tracker_factory = tracker_factory
        self.estimator_factory = estimator_factory
        self.results = LatestObservationStore()
        self._worker: VisionWorker | None = None
        self._cancellation = Event()
        self._handler: Callable = lambda kind, value: None
        self._finished_handler: Callable = lambda: None

    @property
    def active(self) -> bool:
        return self._worker is not None

    def bind(self, event_handler: Callable, finished_handler: Callable) -> None:
        self._handler = event_handler
        self._finished_handler = finished_handler

    def start(self, parameters: DetectionParameters, alpha: float,
              calibration: Calibration | None, status: CalibrationStatus) -> None:
        if self.active:
            raise RuntimeError("Ya existe un Vision Worker activo.")
        self._cancellation = Event()
        self.results.clear()
        factory = lambda: VisionPipeline(self.detector_factory(), self.tracker_factory(),
                                         self.estimator_factory(), parameters, alpha,
                                         calibration, status)
        worker = VisionWorker(self.store, self.results, self._cancellation, factory, self)
        self._worker = worker
        worker.event.connect(self._receive)
        worker.finished.connect(self._finished)
        worker.start()

    def cancel(self) -> None:
        self._cancellation.set()
        self.results.clear()
        self.store.wake_consumers()

    @Slot(str, object)
    def _receive(self, kind: str, value) -> None:
        if self._cancellation.is_set():
            return
        self._handler(kind, self.results.consume() if kind == "result" else value)

    @Slot()
    def _finished(self) -> None:
        worker = self._worker
        if worker is None:
            return
        if not worker.wait(0):
            QTimer.singleShot(0, self._finished)
            return
        self._worker = None
        worker.deleteLater()
        self._finished_handler()
        self.idle.emit()
