import logging
import os
import sqlite3
from collections import deque
from pathlib import Path
from threading import Condition, Event, Lock
from typing import Callable

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot

from ...adapters.storage.filesystem_capture_storage import FileSystemCaptureStorage, resolve_capture_path
from ...adapters.storage.sqlite_vision_repository import SQLiteVisionRepository

logger = logging.getLogger(__name__)


class StorageWorker(QThread):
    result = Signal(int, object, object)
    opened = Signal(object, object)

    def __init__(self, data_root: Path, repository_factory: Callable, parent=None) -> None:
        super().__init__(parent)
        self.data_root = Path(data_root).resolve()
        self.factory = repository_factory
        self.condition = Condition()
        self.jobs = deque()
        self.closing = Event()
        self.repository = None

    def enqueue(self, job) -> None:
        with self.condition:
            self.jobs.append(job)
            self.condition.notify()

    def stop(self) -> None:
        self.closing.set()
        with self.condition:
            self.condition.notify_all()

    def run(self) -> None:
        try:
            self.repository = self.factory(self.data_root / "blanquita_vision.db")
            self.repository.open()
            health = self.repository.health()
            self.validate_settings(health.get("settings", {}))
            self.opened.emit(health, None)
        except Exception as exc:
            logger.error("database_error", exc_info=True)
            if self.repository is not None:
                self.repository.close()
            self.repository = None
            self.opened.emit(None, str(exc))
        try:
            while True:
                with self.condition:
                    self.condition.wait_for(lambda: self.jobs or self.closing.is_set())
                    if not self.jobs:
                        break
                    token, action, payload = self.jobs.popleft()
                result, error = None, None
                for attempt in range(3):
                    try:
                        if self.repository is None:
                            raise OSError("Base de datos no disponible.")
                        result = self.execute(action, payload)
                        error = None
                        break
                    except sqlite3.OperationalError as exc:
                        error = str(exc)
                        if "locked" not in error.lower() and "busy" not in error.lower():
                            break
                        if attempt < 2:
                            self.msleep(200)
                    except Exception as exc:
                        error = str(exc)
                        break
                if error:
                    if payload.get("_capture_record"):
                        error += f"; archivo conservado: {payload['_capture_record']['relative_path']}"
                    logger.error("storage_operation_failed action=%s error=%s", action, error)
                self.result.emit(token, result, error)
        finally:
            if self.repository is not None:
                self.repository.close()

    def execute(self, action: str, payload: dict):
        repository = self.repository
        if action == "insert":
            repository.insert(payload["table"], payload["record"])
        elif action == "session.close":
            repository.close_session(payload["id"], payload["timestamp"], payload["reason"])
        elif action == "calibration.save":
            repository.save_calibration(payload["calibration"])
        elif action == "calibration.invalidate":
            repository.invalidate_calibration(payload["id"], payload["timestamp"])
        elif action == "calibration.invalidate_geometry":
            repository.invalidate_geometry(payload["geometry"], payload["timestamp"])
        elif action == "calibration.load":
            return repository.load_calibration(*payload["geometry"])
        elif action == "calibration.detail":
            return repository.calibration_details(payload["id"])
        elif action == "settings.save":
            settings = payload["settings"]
            self.validate_settings(settings)
            repository.save_settings(settings)
            return repository.load_settings()
        elif action == "capture":
            if "_capture_record" not in payload:
                files = FileSystemCaptureStorage(self.data_root, Path(payload["root"]))
                record = files.save_capture(payload["capture"], payload["format"])
                record.update(payload["metadata"])
                payload["_capture_record"] = record
            repository.insert("captures", payload["_capture_record"])
            return payload["_capture_record"]
        elif action == "query":
            return repository.query(payload["category"], payload.get("filters", {}),
                                    payload.get("limit", 50), payload.get("offset", 0))
        elif action == "export":
            return repository.export(payload["category"], payload.get("filters", {}),
                                     Path(payload["path"]), payload["format"])
        elif action == "capture.open":
            path = resolve_capture_path(self.data_root, payload["path"])
            if not path.is_file():
                raise FileNotFoundError("El archivo de captura no existe.")
            return str(path)
        elif action == "health":
            health = repository.health()
            root = Path(payload["capture_root"])
            health.update(capture_path=str(root), capture_exists=root.is_dir(),
                          capture_writable=os.access(root if root.exists() else root.parent, os.W_OK))
            return health
        else:
            raise ValueError("Operación de storage desconocida.")

    @staticmethod
    def validate_settings(settings: dict) -> None:
        if not isinstance(settings, dict) or set(settings) - {"capture_format", "capture_root", "log_level"}:
            raise ValueError("Ajustes desconocidos o inválidos.")
        if settings.get("capture_format", "jpg") not in ("jpg", "png"):
            raise ValueError("Formato debe ser jpg o png.")
        if "capture_root" in settings and (not isinstance(settings["capture_root"], str) or not settings["capture_root"].strip()):
            raise ValueError("Ruta de capturas vacía o inválida.")
        if settings.get("log_level", "INFO") not in ("INFO", "WARNING", "ERROR"):
            raise ValueError("Nivel de log inválido.")


class QtStorageController(QObject):
    changed = Signal()
    failure = Signal(str)
    idle = Signal()

    def __init__(self, data_root: Path, repository_factory=SQLiteVisionRepository,
                 capacity: int = 256, ordinary_limit: int = 192, parent=None) -> None:
        super().__init__(parent)
        self.data_root = Path(data_root).resolve()
        if capacity < 1 or not 0 <= ordinary_limit <= capacity:
            raise ValueError("Límites de cola inválidos.")
        self.capacity, self.ordinary_limit = capacity, ordinary_limit
        self.health = dict(state="UNINITIALIZED", path=str(self.data_root / "blanquita_vision.db"),
                           queue_depth=0, errors=0, rejected_jobs=0, captures_pending=0, last_error=None)
        self.settings = dict(capture_format="jpg", capture_root=str(self.data_root / "captures"), log_level="INFO")
        self._callbacks = {}
        self._token = 0
        self._ordinary = 0
        self._closing = False
        self._worker = StorageWorker(self.data_root, repository_factory, self)
        self._worker.result.connect(self._completed)
        self._worker.opened.connect(self._opened)
        self._worker.finished.connect(self._finished)
        self.on_ready: list[Callable] = []

    @property
    def active(self) -> bool:
        return self._worker is not None and self.health["state"] not in ("UNINITIALIZED", "CLOSED")

    def start(self) -> None:
        self.health["state"] = "OPENING"
        self._worker.start()
        self.changed.emit()

    def submit(self, action: str, payload: dict, critical=False, callback=None) -> bool:
        rejected = (self._closing or self.health["state"] in ("ERROR", "UNINITIALIZED", "CLOSED")
                    or len(self._callbacks) >= self.capacity
                    or not critical and self._ordinary >= self.ordinary_limit
                    or action == "capture" and self.health["captures_pending"] >= 2)
        if rejected:
            self.health["rejected_jobs"] += 1
            self.health["last_error"] = "Storage no disponible o cola saturada; operación no aceptada."
            if self.health["state"] in ("READY", "DEGRADED"):
                self.health["state"] = "DEGRADED"
            self.changed.emit()
            self.failure.emit(self.health["last_error"])
            if callback:
                callback(None, self.health["last_error"])
            return False
        self._token += 1
        self._callbacks[self._token] = callback, critical, action
        self._ordinary += not critical
        self.health["captures_pending"] += action == "capture"
        self.health["queue_depth"] = len(self._callbacks)
        self._worker.enqueue((self._token, action, payload))
        return True

    @Slot(object, object)
    def _opened(self, health, error) -> None:
        if error:
            self.health.update(state="ERROR", last_error=error, errors=self.health["errors"] + 1)
            self.failure.emit(error)
        else:
            self.health.update(health)
            self.health["state"] = "READY"
            self.settings.update(health.get("settings", {}))
            for callback in tuple(self.on_ready):
                callback()
        self.changed.emit()

    @Slot(int, object, object)
    def _completed(self, token, result, error) -> None:
        entry = self._callbacks.pop(token, None)
        if entry is None:
            return
        callback, critical, action = entry
        self._ordinary -= not critical
        self.health["captures_pending"] -= action == "capture"
        self.health["queue_depth"] = len(self._callbacks)
        if error:
            self.health.update(state="DEGRADED", last_error=error, errors=self.health["errors"] + 1)
            self.failure.emit(error)
        elif not self._closing and action not in ("health", "query", "export", "calibration.load", "calibration.detail", "capture.open"):
            self.health["state"] = "READY"
        if action == "settings.save" and not error:
            self.settings.update(result)
        if action == "health" and not error:
            self.health.update(result)
        if action == "capture" and not error:
            self.health["last_capture"] = result["relative_path"]
        if callback:
            callback(result, error)
        self.changed.emit()

    def shutdown(self) -> None:
        if self._closing or self._worker is None:
            return
        self._closing = True
        self.health["state"] = "CLOSING"
        self._worker.stop()

    @Slot()
    def _finished(self) -> None:
        if self._worker is None:
            return
        if not self._worker.wait(0):
            QTimer.singleShot(0, self._finished)
            return
        self._worker.deleteLater()
        self._worker = None
        self.health["state"] = "CLOSED"
        self.changed.emit()
        self.idle.emit()
