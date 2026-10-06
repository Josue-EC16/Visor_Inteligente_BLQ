from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class ImagePoint:
    u: float
    v: float

    def __post_init__(self) -> None:
        if not all(isfinite(value) for value in (self.u, self.v)):
            raise ValueError("Punto de imagen no finito.")


@dataclass(frozen=True)
class PhysicalPoint2D:
    x: float
    y: float
    unit: str

    def __post_init__(self) -> None:
        if not self.unit.strip() or not all(isfinite(v) for v in (self.x, self.y)):
            raise ValueError("Coordenadas físicas o unidad inválidas.")


@dataclass(frozen=True)
class BoundingBox:
    x: float
    y: float
    width: float
    height: float

    def __post_init__(self) -> None:
        if not all(isfinite(v) for v in (self.x, self.y, self.width, self.height)):
            raise ValueError("Caja no finita.")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Caja sin dimensiones válidas.")

    @property
    def center(self) -> ImagePoint:
        return ImagePoint(self.x + self.width / 2, self.y + self.height / 2)

    def inside(self, width: int, height: int) -> bool:
        return (self.x >= 0 and self.y >= 0 and self.x + self.width <= width
                and self.y + self.height <= height)

    def intersects(self, other: "BoundingBox") -> bool:
        return (min(self.x + self.width, other.x + other.width) > max(self.x, other.x)
                and min(self.y + self.height, other.y + other.height) > max(self.y, other.y))
