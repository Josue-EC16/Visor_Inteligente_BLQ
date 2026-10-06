from typing import Protocol

from ..models.calibration import Calibration


class CalibrationRepositoryPort(Protocol):
    def get_active(self) -> Calibration | None: ...

    def set_active(self, calibration: Calibration) -> None: ...

    def invalidate(self) -> None: ...
