from dataclasses import dataclass
from math import hypot, isfinite

from ..domain.models.geometry import PhysicalPoint2D
from ..domain.models.position import SpatialPosition


@dataclass(frozen=True)
class AccuracySummary:
    count: int
    mae_x: float
    mae_y: float
    mean_2d_error: float
    maximum_2d_error: float


class AccuracyAccumulator:
    """Agregados efímeros de puntos independientes; memoria constante."""

    def __init__(self) -> None:
        self.count = 0
        self.sum_x = self.sum_y = self.sum_2d = self.max_2d = 0.0

    def add(self, estimated: SpatialPosition, reference: PhysicalPoint2D) -> AccuracySummary:
        if estimated.x is None or estimated.y is None or estimated.unit != reference.unit:
            raise ValueError("Estimación y referencia requieren X/Y válidos y la misma unidad.")
        error_x, error_y = abs(estimated.x - reference.x), abs(estimated.y - reference.y)
        distance = hypot(error_x, error_y)
        if not all(isfinite(value) for value in (error_x, error_y, distance)):
            raise ValueError("Error físico no finito.")
        self.count += 1
        self.sum_x += error_x
        self.sum_y += error_y
        self.sum_2d += distance
        self.max_2d = max(self.max_2d, distance)
        return AccuracySummary(self.count, self.sum_x / self.count, self.sum_y / self.count,
                               self.sum_2d / self.count, self.max_2d)
