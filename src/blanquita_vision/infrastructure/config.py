from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    backend: str = "AUTO"
    discovery_indices: tuple[int, ...] = tuple(range(10))
    shutdown_timeout_ms: int = 5000
