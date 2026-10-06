from typing import Callable

import cv2
import numpy as np

from ...domain.models.frame import Frame
from ...domain.models.geometry import BoundingBox
from ...domain.models.tracking import TrackingResult, TrackingState


class CsrtTracker:
    def __init__(self, factory: Callable | None = None) -> None:
        self._factory = factory or self.available_factory()
        self._tracker = None

    @staticmethod
    def available_factory() -> Callable:
        factory = getattr(cv2, "TrackerCSRT_create", None)
        if factory is None:
            factory = getattr(getattr(cv2, "legacy", None), "TrackerCSRT_create", None)
        if factory is None:
            raise RuntimeError("CSRT no está disponible en el OpenCV aprobado.")
        return factory

    @staticmethod
    def _image(frame: Frame):
        image = np.asarray(frame.image)
        if image.ndim != 3 or image.shape[2] not in (3, 4):
            raise ValueError("CSRT requiere imagen de color compatible.")
        if image.shape[2] == 4:
            image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
        return np.ascontiguousarray(image)

    def initialize(self, frame: Frame, box: BoundingBox) -> None:
        self.reset()
        if not box.inside(frame.width, frame.height):
            raise ValueError("Caja de inicialización fuera del frame.")
        self._tracker = (self._factory or self.available_factory())()
        bounds = tuple(int(v) for v in (box.x, box.y, box.width, box.height))
        if bounds[2] <= 0 or bounds[3] <= 0:
            raise ValueError("Caja de inicialización demasiado pequeña.")
        result = self._tracker.init(self._image(frame), bounds)
        if result is False:
            self.reset()
            raise RuntimeError("CSRT rechazó la inicialización.")

    def update(self, frame: Frame) -> TrackingResult:
        if self._tracker is None:
            return TrackingResult(TrackingState.INACTIVE, None, None, "csrt", frame.captured_at)
        try:
            success, values = self._tracker.update(self._image(frame))
            if not success:
                raise ValueError("Seguimiento perdido.")
            box = BoundingBox(*(float(v) for v in values))
            if not box.inside(frame.width, frame.height):
                raise ValueError("Caja de seguimiento inválida.")
            return TrackingResult(TrackingState.TRACKING, box, box.center, "csrt", frame.captured_at)
        except (cv2.error, ValueError):
            self.reset()
            return TrackingResult(TrackingState.LOST, None, None, "csrt", frame.captured_at)

    def reset(self) -> None:
        self._tracker = None
