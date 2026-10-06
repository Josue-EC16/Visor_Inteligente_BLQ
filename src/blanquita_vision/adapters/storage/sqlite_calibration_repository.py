from dataclasses import replace
from datetime import datetime, timezone
from threading import Lock

from ...domain.models.calibration import CalibrationStatus
from ...domain.models.protocol import utc_text
from ...application.report_mapper import calibration_in_mm


class SQLiteCalibrationRepository:
    """Contrato síncrono en memoria; I/O delegado al Storage Worker."""

    def __init__(self, storage) -> None:
        self.storage = storage
        self._lock = Lock()
        self._active = None
        self._persisted_id = None
        self.geometry = None

    def get_active(self):
        with self._lock:
            return self._active

    def set_active(self, calibration) -> None:
        calibration = calibration_in_mm(calibration)
        with self._lock:
            previous = self._active
            self._active = calibration
        if self._persisted_id != calibration.id or previous is None or previous.status is not CalibrationStatus.VALID:
            def saved(result, error):
                if not error and self._active is not None and self._active.id == calibration.id:
                    self._persisted_id = calibration.id
            self.storage.submit("calibration.save", {"calibration": calibration}, critical=True,
                                callback=saved)

    def invalidate(self) -> None:
        with self._lock:
            active = self._active
            if active is not None:
                self._active = replace(active, status=CalibrationStatus.INVALID)
        if active is not None:
            self.storage.submit("calibration.invalidate", {"id": active.id, "timestamp": utc_text(datetime.now(timezone.utc))}, critical=True)
        elif self.geometry is not None:
            self.storage.submit("calibration.invalidate_geometry", {"geometry": self.geometry,
                                                                     "timestamp": utc_text(datetime.now(timezone.utc))}, critical=True)

    def accept_loaded(self, calibration) -> None:
        with self._lock:
            self._active = calibration
        self._persisted_id = calibration.id
