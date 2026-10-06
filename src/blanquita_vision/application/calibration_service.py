import logging
from datetime import datetime, timezone
from typing import Callable
from uuid import uuid4

from ..domain.models.calibration import Calibration, CalibrationPoint, CalibrationStatus
from ..domain.ports.calibration_repository_port import CalibrationRepositoryPort
from ..domain.ports.calibration_solver_port import CalibrationSolverPort

logger = logging.getLogger(__name__)


class CalibrationService:
    def __init__(self, repository: CalibrationRepositoryPort, solver: CalibrationSolverPort) -> None:
        self.repository = repository
        self.solver = solver
        self.status = CalibrationStatus.UNCALIBRATED
        self.geometry: tuple[str, int, int] | None = None
        self.on_change: list[Callable[[], None]] = []
        self.revision = 0

    def _notify(self) -> None:
        self.revision += 1
        for callback in tuple(self.on_change):
            callback()

    def observe_geometry(self, camera_id: str, width: int | None, height: int | None) -> None:
        active = self.repository.get_active()
        if active is not None and active.status is CalibrationStatus.VALID:
            changed = camera_id != active.camera_id
            if width is not None and height is not None:
                changed |= (width, height) != (active.width, active.height)
            if changed:
                self.invalidate()
        if width is not None and height is not None:
            self.geometry = camera_id, width, height

    def begin(self) -> None:
        self.repository.invalidate()
        self.status = CalibrationStatus.CALIBRATING
        logger.info("calibration_started")
        self._notify()

    def compute(self, points: tuple[CalibrationPoint, ...], camera_id: str,
                width: int, height: int) -> Calibration:
        if len(points) != 4:
            raise ValueError("Se requieren cuatro correspondencias completas.")
        if any(not 0 <= p.image.u < width or not 0 <= p.image.v < height for p in points):
            raise ValueError("Los puntos de imagen deben estar dentro del frame.")
        matrix, error = self.solver.solve(points)
        return Calibration(str(uuid4()), camera_id, width, height, points, matrix,
                           points[0].physical.unit, datetime.now(timezone.utc),
                           internal_reprojection_error=error)

    def apply(self, calibration: Calibration) -> None:
        if calibration.status is not CalibrationStatus.VALID:
            raise ValueError("La calibración candidata no es válida.")
        if self.geometry != (calibration.camera_id, calibration.width, calibration.height):
            raise ValueError("La cámara o resolución cambiaron; vuelve a calibrar.")
        self.repository.set_active(calibration)
        self.status = CalibrationStatus.VALID
        logger.info("calibration_created id=%s", calibration.id)
        self._notify()

    def invalidate(self) -> None:
        self.repository.invalidate()
        self.status = CalibrationStatus.INVALID
        logger.warning("calibration_invalidated")
        self._notify()

    def fail(self, message: str) -> None:
        self.repository.invalidate()
        self.status = CalibrationStatus.ERROR
        logger.error("calibration_error %s", message)
        self._notify()

    def active(self) -> Calibration | None:
        calibration = self.repository.get_active()
        if self.status is CalibrationStatus.VALID and calibration is not None:
            return calibration if calibration.status is CalibrationStatus.VALID else None
        return None
