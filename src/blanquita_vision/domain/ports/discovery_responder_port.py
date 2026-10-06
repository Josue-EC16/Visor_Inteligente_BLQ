from typing import Protocol

from ..models.discovery import DiscoveryStatus


class DiscoveryResponderPort(Protocol):
    def start(self) -> None: ...

    def stop(self) -> None: ...

    def snapshot(self) -> DiscoveryStatus: ...

    @property
    def active(self) -> bool: ...
