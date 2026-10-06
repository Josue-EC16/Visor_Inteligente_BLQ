from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class RecoveryPolicy:
    attempts: int = 3
    interval_seconds: float = 2.0
    invalid_read_limit: int = 3

    def __post_init__(self) -> None:
        if self.attempts < 1 or not isfinite(self.interval_seconds):
            raise ValueError("Política de recuperación inválida.")
        if self.interval_seconds < 0 or self.invalid_read_limit < 1:
            raise ValueError("Política de recuperación inválida.")
