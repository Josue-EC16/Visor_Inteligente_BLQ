from dataclasses import dataclass


@dataclass(frozen=True)
class CameraDevice:
    id: str
    index: int
    display_name: str
    available: bool = True

    def __post_init__(self) -> None:
        if self.index < 0 or not self.id or not self.display_name:
            raise ValueError("Dispositivo de cámara inválido.")
