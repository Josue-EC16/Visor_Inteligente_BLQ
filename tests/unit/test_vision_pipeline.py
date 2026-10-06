from blanquita_vision.application.vision_pipeline import VisionPipeline
from blanquita_vision.domain.models.calibration import CalibrationStatus
from blanquita_vision.domain.models.tracking import TrackingState
from tests.fixtures.vision_fakes import (
    FakeDetector, FakePositionEstimator, FakeTracker, color_frame, test_parameters as parameters,
)
from tests.unit.test_calibration_position_filter import calibrated_service


def pipeline(detector=None, tracker=None, calibrated=True):
    calibration = calibrated_service()[1] if calibrated else None
    return VisionPipeline(detector or FakeDetector(), tracker or FakeTracker(), FakePositionEstimator(),
                          parameters(), 0.5, calibration,
                          CalibrationStatus.VALID if calibrated else CalibrationStatus.UNCALIBRATED)


def test_tc_01_029_internal_observation_is_frame_consistent():
    result = pipeline().process(color_frame(9))
    observation = result.observation
    assert observation.frame_sequence == result.frame.sequence == 9
    assert observation.timestamp == result.frame.captured_at
    assert observation.position.raw_position.z is None
    assert observation.position.filtered_position.z is None
    assert observation.position.angle is None
    assert observation.position.raw_position.x == 55
    assert observation.tracking.source == "detection"


def test_tc_01_018_detection_without_calibration_has_no_physical_position():
    result = pipeline(calibrated=False).process(color_frame())
    assert result.observation.detection.detected
    assert result.observation.position is None


def test_tc_01_011_012_loss_redetects_and_ema_restarts():
    tracker = FakeTracker([False])
    detector = FakeDetector()
    service = pipeline(detector, tracker)
    first = service.process(color_frame(0))
    second = service.process(color_frame(1))
    assert tracker.initializations == 2
    assert detector.calls == 2
    assert second.metrics.lost_tracking == 1
    assert second.metrics.reacquisitions == 1
    assert second.observation.position.raw_position == second.observation.position.filtered_position
    detector.visible = False
    lost = service.process(color_frame(2))
    assert lost.observation.position is None
    assert lost.observation.tracking.state is TrackingState.LOST
    detector.visible = True
    recovered = service.process(color_frame(3))
    assert recovered.observation.position.raw_position == recovered.observation.position.filtered_position


def test_tracking_exception_degrades_to_redetection():
    tracker = FakeTracker([RuntimeError("fallo tracker")])
    service = pipeline(tracker=tracker)
    service.process(color_frame())
    result = service.process(color_frame(1))
    assert result.observation.tracking.state is TrackingState.TRACKING
    assert tracker.initializations == 2


def test_drift_without_matching_detection_reinitializes_tracker():
    class DriftingTracker(FakeTracker):
        def update(self, frame):
            from blanquita_vision.domain.models.geometry import BoundingBox
            from blanquita_vision.domain.models.tracking import TrackingResult
            box = BoundingBox(110, 80, 20, 20)
            return TrackingResult(TrackingState.TRACKING, box, box.center, "csrt", frame.captured_at)
    tracker = DriftingTracker()
    service = pipeline(tracker=tracker)
    service.process(color_frame())
    result = service.process(color_frame(1))
    assert result.observation.tracking.source == "detection"
    assert tracker.initializations == 2


def test_resolution_change_never_uses_old_homography_before_ui_notices():
    import numpy as np
    from dataclasses import replace
    service = pipeline()
    service.process(color_frame())
    frame = replace(color_frame(1), width=320, height=240,
                    image=np.zeros((240, 320, 3), dtype=np.uint8))
    result = service.process(frame)
    assert result.observation.detection.detected
    assert result.observation.position is None
    assert result.observation.calibration_status is CalibrationStatus.INVALID
