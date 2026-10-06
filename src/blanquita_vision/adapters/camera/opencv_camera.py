import logging
from datetime import datetime, timezone
from math import isfinite
from threading import Event
from typing import Callable

import cv2
import numpy as np

from ...domain.models.camera_device import CameraDevice
from ...domain.models.camera_state import CameraError
from ...domain.models.capture_configuration import (
    CaptureConfiguration, CaptureProperties,
)
from ...domain.models.frame import Frame

logger = logging.getLogger(__name__)


class OpenCvCamera:
    """El recurso se utiliza exclusivamente desde el worker propietario."""

    def __init__(
        self,
        indices: tuple[int, ...] = tuple(range(10)),
        backend: str = "AUTO",
        capture_factory: Callable = cv2.VideoCapture,
        cancellation: Event | None = None,
    ) -> None:
        self._indices = indices
        self._backend = backend.upper()
        self._factory = capture_factory
        self._capture = None
        self._sequence = 0
        self._cancellation = cancellation or Event()

    @staticmethod
    def backend_id(name: str) -> int:
        if name.upper() == "AUTO":
            return cv2.CAP_ANY
        constant = getattr(cv2, "CAP_" + name.upper(), None)
        if not isinstance(constant, int):
            raise CameraError("backend_invalid", "Backend de captura desconocido.")
        if (constant not in cv2.videoio_registry.getBackends()
                or not cv2.videoio_registry.hasBackend(constant)):
            raise CameraError(
                "backend_unavailable",
                f"Backend {name.upper()} no disponible en este entorno de OpenCV. "
                "Selecciona AUTO o un backend disponible.",
            )
        return constant

    def discover(self) -> list[CameraDevice]:
        if self.is_open:
            raise CameraError("camera_busy", "Detén la cámara antes de actualizar.")
        backend = self.backend_id(self._backend)
        devices = []
        for index in self._indices:
            if self._cancellation.is_set():
                break
            capture = None
            try:
                capture = self._factory(index, backend)
                if capture.isOpened():
                    devices.append(CameraDevice(str(index), index, f"Cámara {index}"))
            except Exception:
                logger.warning("camera_discovery_index_failed index=%s", index,
                               exc_info=True)
            finally:
                if capture is not None:
                    try:
                        capture.release()
                    except Exception:
                        logger.warning("camera_discovery_release_failed index=%s",
                                       index, exc_info=True)
        return devices

    @staticmethod
    def _positive(value: float, integer: bool = False):
        if not isfinite(value) or value <= 0:
            return None
        return int(value) if integer else float(value)

    def open(self, config: CaptureConfiguration) -> CaptureProperties:
        self.close()
        try:
            backend = self.backend_id(config.backend)
            self._capture = self._factory(config.device_index, backend)
            if not self._capture.isOpened():
                raise CameraError(
                    "open_failed",
                    "No se pudo abrir la cámara. Comprueba disponibilidad y permisos.",
                )
            for key, value in (
                (cv2.CAP_PROP_FRAME_WIDTH, config.requested_width),
                (cv2.CAP_PROP_FRAME_HEIGHT, config.requested_height),
                (cv2.CAP_PROP_FPS, config.requested_fps),
            ):
                if value is not None and not self._capture.set(key, value):
                    raise CameraError("configuration_rejected",
                                      "La cámara rechazó la configuración solicitada.")
            try:
                backend_name = self._capture.getBackendName()
            except cv2.error:
                backend_name = None
            return CaptureProperties(
                self._positive(self._capture.get(cv2.CAP_PROP_FRAME_WIDTH), True),
                self._positive(self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT), True),
                self._positive(self._capture.get(cv2.CAP_PROP_FPS)),
                backend_name,
            )
        except Exception as exc:
            self.close()
            if isinstance(exc, CameraError):
                raise
            raise CameraError("open_failed", "Error al abrir la cámara.") from exc

    def read(self) -> Frame | None:
        if not self.is_open:
            return None
        try:
            success, image = self._capture.read()
            if not success or not isinstance(image, np.ndarray) or image.size == 0:
                return None
            if image.ndim not in (2, 3) or min(image.shape[:2]) <= 0:
                return None
            if image.ndim == 3 and image.shape[2] not in (1, 3, 4):
                return None
            if image.dtype != np.uint8:
                return None
            height, width = image.shape[:2]
            owned_image = image.copy()
            owned_image.setflags(write=False)
            frame = Frame(self._sequence, datetime.now(timezone.utc),
                          width, height, owned_image)
            self._sequence += 1
            return frame
        except cv2.error:
            logger.warning("camera_read_failed", exc_info=True)
            return None

    def close(self) -> None:
        capture, self._capture = self._capture, None
        if capture is not None:
            try:
                capture.release()
            except Exception:
                logger.warning("camera_release_failed", exc_info=True)

    @property
    def is_open(self) -> bool:
        return self._capture is not None and self._capture.isOpened()
