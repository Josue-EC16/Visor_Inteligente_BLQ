from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from math import isfinite

from .geometry import ImagePoint, PhysicalPoint2D

Matrix3x3 = tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]


class CalibrationStatus(Enum):
    UNCALIBRATED = "UNCALIBRATED"
    CALIBRATING = "CALIBRATING"
    VALID = "VALID"
    INVALID = "INVALID"
    ERROR = "ERROR"


@dataclass(frozen=True)
class CalibrationPoint:
    image: ImagePoint
    physical: PhysicalPoint2D


@dataclass(frozen=True)
class Calibration:
    id: str
    camera_id: str
    width: int
    height: int
    points: tuple[CalibrationPoint, ...]
    homography: Matrix3x3
    unit: str
    created_at: datetime
    status: CalibrationStatus = CalibrationStatus.VALID
    internal_reprojection_error: float | None = None

    def __post_init__(self) -> None:
        if not self.id or not self.camera_id or self.width <= 0 or self.height <= 0:
            raise ValueError("Identidad o resolución de calibración inválidas.")
        if len(self.points) != 4 or not self.unit.strip():
            raise ValueError("Se requieren cuatro correspondencias y una unidad.")
        if any(p.physical.unit != self.unit for p in self.points):
            raise ValueError("Las unidades de calibración deben coincidir.")
        if len(self.homography) != 3 or any(len(row) != 3 for row in self.homography):
            raise ValueError("Homografía debe ser una matriz 3×3.")
        if not all(isfinite(v) for row in self.homography for v in row):
            raise ValueError("Homografía no finita.")
        error = self.internal_reprojection_error
        if error is not None and (not isfinite(error) or error < 0):
            raise ValueError("Error interno de reproyección inválido.")
