from collections import deque
from datetime import datetime, timezone
from threading import get_ident

import cv2
import numpy as np

from blanquita_vision.domain.models.detection import Detection, DetectionParameters
from blanquita_vision.domain.models.frame import Frame
from blanquita_vision.domain.models.geometry import BoundingBox
from blanquita_vision.domain.models.position import SpatialPosition
from blanquita_vision.domain.models.tracking import TrackingResult, TrackingState
from tests.fixtures.fake_camera import FakeCamera


def test_parameters(**changes):
    values = dict(hue_min=90, hue_max=100, saturation_min=100, saturation_max=255,
                  value_min=100, value_max=255, min_area=20, minimum_confidence=0.1)
    values.update(changes)
    return DetectionParameters(**values)


def color_frame(sequence=0, visible=True, offset=0):
    hsv = np.zeros((120, 160, 3), dtype=np.uint8)
    if visible:
        hsv[35:65, 40 + offset:70 + offset] = (95, 180, 220)
    image = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    return Frame(sequence, datetime.now(timezone.utc), 160, 120, image)


class ColorCamera(FakeCamera):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.visible = True

    def read(self):
        self._record_thread()
        self.read_calls += 1
        if self.cancellation.wait(self.delay) or not self.is_open:
            return None
        result = color_frame(self._sequence, self.visible)
        self._sequence += 1
        return result


class FakeDetector:
    def __init__(self, visible=True):
        self.visible = visible
        self.calls = 0
        self.threads = []

    def detect(self, frame, parameters):
        self.calls += 1
        self.threads.append(get_ident())
        box = BoundingBox(40, 35, 30, 30)
        return Detection(self.visible, "gancho", box if self.visible else None,
                         box.center if self.visible else None, 0.8 if self.visible else 0,
                         frame.captured_at, frame.sequence)


class FakeTracker:
    def __init__(self, outcomes=()):
        self.outcomes = deque(outcomes)
        self.box = None
        self.initializations = 0
        self.updates = 0
        self.resets = 0
        self.threads = []

    def initialize(self, frame, box):
        self.threads.append(get_ident())
        self.box = box
        self.initializations += 1

    def update(self, frame):
        self.threads.append(get_ident())
        self.updates += 1
        if self.outcomes:
            result = self.outcomes.popleft()
            if isinstance(result, Exception):
                raise result
            if result is False:
                return TrackingResult(TrackingState.LOST, None, None, "csrt", frame.captured_at)
        return TrackingResult(TrackingState.TRACKING, self.box, self.box.center, "csrt", frame.captured_at)

    def reset(self):
        self.resets += 1
        self.box = None


class FakePositionEstimator:
    def estimate(self, point, calibration):
        return SpatialPosition(point.u, point.v, None, calibration.unit)
