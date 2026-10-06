from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from math import isfinite

from .geometry import BoundingBox, ImagePoint


class DetectionState(Enum):
    DISABLED = "DISABLED"
    SEARCHING = "SEARCHING"
    DETECTED = "DETECTED"
    NOT_DETECTED = "NOT_DETECTED"
    ERROR = "ERROR"


@dataclass(frozen=True)
class DetectionParameters:
    hue_min: int
    hue_max: int
    saturation_min: int
    saturation_max: int
    value_min: int
    value_max: int
    min_area: float
    minimum_confidence: float
    max_area: float | None = None
    morphology_enabled: bool = False
    morphology_kernel_size: int | None = None

    def __post_init__(self) -> None:
        for low, high, maximum in (
            (self.hue_min, self.hue_max, 179),
            (self.saturation_min, self.saturation_max, 255),
            (self.value_min, self.value_max, 255),
        ):
            if not isinstance(low, int) or not isinstance(high, int) or not 0 <= low <= high <= maximum:
                raise ValueError("Rangos HSV inválidos (H: 0–179; S/V: 0–255).")
        if not isfinite(self.min_area) or self.min_area < 0:
            raise ValueError("Área mínima inválida.")
        if self.max_area is not None:
            if not isfinite(self.max_area) or self.max_area < self.min_area:
                raise ValueError("Área máxima inválida.")
        if not isfinite(self.minimum_confidence) or not 0 <= self.minimum_confidence <= 1:
            raise ValueError("Calidad mínima debe estar entre 0 y 1.")
        if self.morphology_enabled:
            size = self.morphology_kernel_size
            if not isinstance(size, int) or size < 1 or size % 2 == 0:
                raise ValueError("Kernel morfológico debe ser entero positivo impar.")


@dataclass(frozen=True)
class DetectionCandidate:
    bounding_box: BoundingBox
    centroid: ImagePoint
    contour_area: float
    mask_coverage: float
    geometry_score: float
    confidence: float


@dataclass(frozen=True)
class Detection:
    detected: bool
    object_name: str
    bounding_box: BoundingBox | None
    centroid: ImagePoint | None
    confidence: float
    timestamp: datetime
    frame_sequence: int
    ambiguous: bool = False

    def __post_init__(self) -> None:
        if not isfinite(self.confidence) or not 0 <= self.confidence <= 1:
            raise ValueError("Calidad de detección inválida.")
        if self.detected and (self.bounding_box is None or self.centroid is None):
            raise ValueError("Detección válida requiere caja y centroide.")
