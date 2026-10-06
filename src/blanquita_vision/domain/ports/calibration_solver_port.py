from typing import Protocol

from ..models.calibration import CalibrationPoint, Matrix3x3


class CalibrationSolverPort(Protocol):
    def solve(self, points: tuple[CalibrationPoint, ...]) -> tuple[Matrix3x3, float]: ...
