from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


class FrameImage(Protocol):
    @property
    def size(self) -> int: ...

    def copy(self) -> "FrameImage": ...


@dataclass(frozen=True)
class Frame:
    sequence: int
    captured_at: datetime
    width: int
    height: int
    image: FrameImage

    def __post_init__(self) -> None:
        if self.sequence < 0 or self.width <= 0 or self.height <= 0:
            raise ValueError("Metadatos de frame inválidos.")
        if self.image is None or self.image.size <= 0:
            raise ValueError("Imagen de frame vacía.")


@dataclass(frozen=True)
class CapturedFrame:
    source_sequence: int
    captured_at: datetime
    image_copy: FrameImage
