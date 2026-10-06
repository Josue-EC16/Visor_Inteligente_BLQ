from dataclasses import replace

import cv2
import numpy as np
import pytest

from blanquita_vision.adapters.detection.csrt_tracker import CsrtTracker
from blanquita_vision.adapters.detection.opencv_hook_detector import OpenCvHookDetector
from blanquita_vision.domain.models.frame import Frame
from blanquita_vision.domain.models.geometry import BoundingBox
from blanquita_vision.domain.models.tracking import TrackingState
from tests.fixtures.vision_fakes import color_frame, test_parameters as parameters


def test_tc_01_004_color_fixture_and_frame_metadata():
    frame = color_frame(42)
    detector = OpenCvHookDetector()
    detection = detector.detect(frame, parameters())
    assert detection.detected
    assert detection.object_name == "gancho"
    assert detection.timestamp == frame.captured_at
    assert detection.frame_sequence == 42
    assert detection.bounding_box == BoundingBox(40, 35, 30, 30)
    assert detection.centroid.u == pytest.approx(54.5)
    assert 0 <= detection.confidence <= 1
    candidate = detector.candidates[0]
    assert detection.confidence == pytest.approx(candidate.geometry_score * candidate.mask_coverage)


def test_tc_01_005_no_target_and_quality_threshold():
    detector = OpenCvHookDetector()
    assert not detector.detect(color_frame(visible=False), parameters()).detected
    image = color_frame().image.copy()
    image[42:60, 45:65] = 0
    frame = replace(color_frame(), image=image)
    assert not detector.detect(frame, parameters(minimum_confidence=0.95)).detected


def test_tc_01_006_ambiguous_equal_candidates_not_selected():
    frame = color_frame()
    image = frame.image.copy()
    image[75:105, 95:125] = image[35:65, 40:70]
    result = OpenCvHookDetector().detect(replace(frame, image=image), parameters())
    assert not result.detected
    assert result.ambiguous
    assert result.bounding_box is None


def test_area_filter_excludes_small_distractor():
    frame = color_frame()
    image = frame.image.copy()
    image[5:8, 5:8] = image[35, 40]
    detector = OpenCvHookDetector()
    assert detector.detect(replace(frame, image=image), parameters()).detected
    assert len(detector.candidates) == 1
    assert not detector.detect(frame, parameters(max_area=100)).detected


@pytest.mark.parametrize("changes", [
    {"hue_min": -1}, {"hue_max": 180}, {"hue_min": 110},
    {"saturation_min": 300}, {"value_max": -1}, {"min_area": float("nan")},
    {"max_area": 1}, {"minimum_confidence": 1.1},
    {"morphology_enabled": True, "morphology_kernel_size": 2},
])
def test_tc_01_007_invalid_parameters(changes):
    with pytest.raises(ValueError):
        parameters(**changes)


def test_morphology_preserves_source_coordinates():
    detection = OpenCvHookDetector().detect(color_frame(), parameters(
        morphology_enabled=True, morphology_kernel_size=3,
    ))
    assert detection.bounding_box == BoundingBox(40, 35, 30, 30)


def test_gray_frame_is_rejected_without_inventing_color():
    frame = color_frame()
    gray = cv2.cvtColor(frame.image, cv2.COLOR_BGR2GRAY)
    with pytest.raises(ValueError, match="BGR"):
        OpenCvHookDetector().detect(replace(frame, image=gray), parameters())


def test_morphology_rejects_kernel_larger_than_frame():
    with pytest.raises(ValueError, match="kernel"):
        OpenCvHookDetector().detect(color_frame(), parameters(
            morphology_enabled=True, morphology_kernel_size=1001,
        ))


def test_tc_01_010_real_csrt_on_synthetic_frame():
    tracker = CsrtTracker()
    frame = color_frame()
    tracker.initialize(frame, BoundingBox(40, 35, 30, 30))
    result = tracker.update(color_frame(1, offset=2))
    assert result.state is TrackingState.TRACKING
    assert result.bounding_box.inside(160, 120)
    assert result.source == "csrt"
    tracker.reset()
    assert tracker.update(frame).state is TrackingState.INACTIVE


@pytest.mark.parametrize("values", [(False, (0, 0, 0, 0)), (True, (-1, 0, 20, 20)),
                                   (True, (0, 0, float("nan"), 20))])
def test_invalid_csrt_result_is_lost(values):
    class TrackerDouble:
        def init(self, image, box):
            return None
        def update(self, image):
            return values
    tracker = CsrtTracker(TrackerDouble)
    tracker.initialize(color_frame(), BoundingBox(40, 35, 30, 30))
    assert tracker.update(color_frame()).state is TrackingState.LOST


def test_csrt_unavailable_is_explicit(monkeypatch):
    monkeypatch.delattr(cv2, "TrackerCSRT_create", raising=False)
    monkeypatch.delattr(cv2.legacy, "TrackerCSRT_create", raising=False)
    with pytest.raises(RuntimeError, match="CSRT"):
        CsrtTracker()
