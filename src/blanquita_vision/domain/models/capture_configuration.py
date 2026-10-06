from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class CaptureConfiguration:
    device_index: int
    # Identificador opaco: únicamente infraestructura/adapter lo interpreta.
    backend: str = "AUTO"
    requested_width: int | None = None
    requested_height: int | None = None
    requested_fps: float | None = None

    def __post_init__(self) -> None:
        if self.device_index < 0 or not self.backend:
            raise ValueError("Configuración de dispositivo inválida.")
        for value in (self.requested_width, self.requested_height):
            if value is not None and value <= 0:
                raise ValueError("Dimensiones de captura inválidas.")
        if self.requested_fps is not None:
            if not isfinite(self.requested_fps) or self.requested_fps <= 0:
                raise ValueError("FPS solicitado inválido.")


@dataclass(frozen=True)
class CaptureProperties:
    width: int | None = None
    height: int | None = None
    reported_fps: float | None = None
    backend_name: str | None = None
