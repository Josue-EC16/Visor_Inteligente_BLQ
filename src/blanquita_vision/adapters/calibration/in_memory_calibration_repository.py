from dataclasses import replace
from threading import Lock

from ...domain.models.calibration import Calibration, CalibrationStatus


class InMemoryCalibrationRepository:
    def __init__(self) -> None:
        self._calibration: Calibration | None = None
        self._lock = Lock()

    def get_active(self) -> Calibration | None:
        with self._lock:
            return self._calibration

    def set_active(self, calibration: Calibration) -> None:
        with self._lock:
            self._calibration = calibration

    def invalidate(self) -> None:
        with self._lock:
            if self._calibration is not None:
                self._calibration = replace(self._calibration, status=CalibrationStatus.INVALID)
