from math import isfinite

from ..domain.models.position import EmaFilterState, SpatialPosition


class EmaPositionFilter:
    def __init__(self, alpha: float) -> None:
        if not isfinite(alpha) or not 0 < alpha <= 1:
            raise ValueError("Alpha EMA debe cumplir 0 < alpha ≤ 1.")
        self.state = EmaFilterState(alpha)
        self._unit: str | None = None

    def reset(self) -> None:
        self.state.initialized = False
        self.state.last_x = self.state.last_y = None
        self._unit = None

    def update(self, raw_position: SpatialPosition) -> SpatialPosition:
        if raw_position.x is None or raw_position.y is None:
            self.reset()
            return SpatialPosition()
        if raw_position.unit != self._unit:
            self.reset()
        alpha = self.state.alpha
        if not self.state.initialized:
            x, y = raw_position.x, raw_position.y
        else:
            x = alpha * raw_position.x + (1 - alpha) * self.state.last_x
            y = alpha * raw_position.y + (1 - alpha) * self.state.last_y
        self.state.last_x, self.state.last_y = x, y
        self.state.initialized = True
        self._unit = raw_position.unit
        return SpatialPosition(x, y, None, raw_position.unit)
