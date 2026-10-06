from typing import Protocol


class DiagnosticsProviderPort(Protocol):
    def snapshot(self) -> dict: ...
