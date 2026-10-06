import logging
from dataclasses import dataclass
from time import perf_counter

from ..domain.models.calibration import Calibration, CalibrationStatus
from ..domain.models.detection import DetectionParameters, DetectionState
from ..domain.models.frame import Frame
from ..domain.models.position import PositionEstimate, PositionStatus
from ..domain.models.tracking import TrackingResult, TrackingState
from ..domain.models.vision_observation import VisionObservation, VisionPipelineState
from ..domain.ports.detector_port import DetectorPort
from ..domain.ports.position_estimator_port import PositionEstimatorPort
from ..domain.ports.tracker_port import TrackerPort
from .position_filter import EmaPositionFilter

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PipelineMetrics:
    preprocess_ms: float | None
    detection_ms: float | None
    tracking_ms: float
    position_ms: float | None
    filter_ms: float | None
    total_ms: float
    frames_processed: int
    skipped_frames: int
    pipeline_fps: float
    detections: int
    lost_tracking: int
    reacquisitions: int


@dataclass(frozen=True)
class ProcessedFrame:
    frame: Frame
    observation: VisionObservation
    metrics: PipelineMetrics


class VisionPipeline:
    def __init__(self, detector: DetectorPort, tracker: TrackerPort,
                 estimator: PositionEstimatorPort, parameters: DetectionParameters,
                 alpha: float, calibration: Calibration | None,
                 calibration_status: CalibrationStatus) -> None:
        self.detector = detector
        self.tracker = tracker
        self.estimator = estimator
        self.parameters = parameters
        self.filter = EmaPositionFilter(alpha)
        self.calibration = calibration
        self.calibration_status = calibration_status
        self._tracking = False
        self._previous_detected = False
        self._ever_tracked = False
        self._position_available = False
        self._processed = self._detections = self._lost = self._reacquired = 0
        self._started = perf_counter()
        self._dimensions: tuple[int, int] | None = None

    def reset(self) -> None:
        self.tracker.reset()
        self.filter.reset()
        self._tracking = False

    def process(self, frame: Frame, skipped_frames: int = 0) -> ProcessedFrame:
        started = perf_counter()
        dimensions = (frame.width, frame.height)
        if self._dimensions is not None and dimensions != self._dimensions:
            self.reset()
        self._dimensions = dimensions
        calibration = self.calibration
        calibration_status = self.calibration_status
        if calibration is not None and dimensions != (calibration.width, calibration.height):
            calibration = None
            calibration_status = CalibrationStatus.INVALID
        detection = self.detector.detect(frame, self.parameters)
        if detection.detected and not detection.bounding_box.inside(frame.width, frame.height):
            raise ValueError("El detector devolvió una caja fuera del frame fuente.")
        detector_finished = perf_counter()
        tracking_started = detector_finished
        had_tracking = self._tracking
        if detection.detected:
            self._detections += 1
            if not self._previous_detected:
                logger.info("hook_detected")
            tracked = None
            if self._tracking:
                try:
                    tracked = self.tracker.update(frame)
                except Exception:
                    logger.warning("tracker_update_failed", exc_info=True)
            compatible = (tracked is not None and tracked.state is TrackingState.TRACKING
                          and tracked.bounding_box is not None
                          and tracked.centroid is not None
                          and tracked.bounding_box.inside(frame.width, frame.height)
                          and tracked.bounding_box.intersects(detection.bounding_box))
            if compatible:
                tracking = tracked
            else:
                if had_tracking:
                    self._lost += 1
                    logger.info("tracker_lost")
                self.reset()
                self.tracker.initialize(frame, detection.bounding_box)
                tracking = TrackingResult(TrackingState.TRACKING, detection.bounding_box,
                                          detection.bounding_box.center, "detection", frame.captured_at)
                self._tracking = True
                if self._ever_tracked:
                    self._reacquired += 1
                    logger.info("tracker_reinitialized")
                else:
                    logger.info("tracker_initialized")
                self._ever_tracked = True
            detection_state = DetectionState.DETECTED
        else:
            if had_tracking:
                self._lost += 1
                logger.info("tracker_lost")
            if self._previous_detected:
                logger.info("hook_lost")
            self.reset()
            tracking = TrackingResult(TrackingState.LOST if had_tracking else TrackingState.INACTIVE,
                                      None, None, "detection", frame.captured_at)
            detection_state = DetectionState.SEARCHING if detection.ambiguous else DetectionState.NOT_DETECTED
        self._previous_detected = detection.detected
        tracking_ms = (perf_counter() - tracking_started) * 1000
        position = None
        position_status = PositionStatus.UNAVAILABLE
        position_ms = filter_ms = None
        if detection.detected and calibration is not None:
            position_started = perf_counter()
            try:
                raw = self.estimator.estimate(tracking.bounding_box.center, calibration)
                if raw.x is None or raw.y is None or raw.z is not None:
                    raise ValueError("El estimador debe producir X/Y válidos y Z no disponible.")
                position_ms = (perf_counter() - position_started) * 1000
                filter_started = perf_counter()
                filtered = self.filter.update(raw)
                filter_ms = (perf_counter() - filter_started) * 1000
                position = PositionEstimate(raw, filtered, detection.confidence,
                                            frame.captured_at, calibrated=True)
                position_status = PositionStatus.FILTERED_AVAILABLE
            except ValueError:
                self.filter.reset()
                position_status = PositionStatus.INVALID
                logger.warning("position_unavailable", exc_info=True)
        else:
            self.filter.reset()
        available = position is not None
        if available != self._position_available:
            logger.info("position_available" if available else "position_unavailable")
            self._position_available = available
        total = (perf_counter() - started) * 1000
        self._processed += 1
        timings = getattr(self.detector, "last_timings", None)
        preprocess_ms, detection_ms = timings if timings is not None else (None, (detector_finished - started) * 1000)
        metrics = PipelineMetrics(preprocess_ms, detection_ms, tracking_ms, position_ms,
                                  filter_ms, total, self._processed, skipped_frames,
                                  self._processed / max(perf_counter() - self._started, 1e-12),
                                  self._detections, self._lost, self._reacquired)
        observation = VisionObservation(frame.sequence, frame.captured_at, detection, tracking,
                                        position, calibration_status, VisionPipelineState.RUNNING,
                                        total, detection_state, position_status)
        return ProcessedFrame(frame, observation, metrics)
