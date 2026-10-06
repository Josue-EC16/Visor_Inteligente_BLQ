from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import cv2
import numpy as np

from ...domain.models.frame import CapturedFrame
from ...domain.models.protocol import utc_text


class FileSystemCaptureStorage:
    def __init__(self, data_root: Path, capture_root: Path) -> None:
        self.data_root = Path(data_root).resolve()
        self.capture_root = Path(capture_root).resolve()

    def save_capture(self, capture: CapturedFrame, format: str) -> dict:
        if format not in ("jpg", "png"):
            raise ValueError("Formato de captura inválido.")
        self.capture_root.mkdir(parents=True, exist_ok=True)
        identifier = str(uuid4())
        path = self.capture_root / f"{identifier}.{format}"
        image = np.asarray(capture.image_copy)
        if format == "jpg" and image.ndim == 3 and image.shape[2] == 4:
            image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
        success, encoded = cv2.imencode("." + format, image)
        if not success:
            raise OSError("No se pudo codificar la captura.")
        with path.open("xb") as output:
            payload = encoded.tobytes()
            if output.write(payload) != len(payload):
                raise OSError("Escritura incompleta de captura.")
            output.flush()
        if path.stat().st_size != len(payload):
            raise OSError("No se verificó la escritura de captura.")
        try:
            stored_path = path.relative_to(self.data_root).as_posix()
        except ValueError:
            stored_path = str(path)
        return dict(capture_id=identifier, created_at_utc=utc_text(capture.captured_at),
                    relative_path=stored_path, format=format, frame_sequence=capture.source_sequence)


def resolve_capture_path(data_root: Path, stored_path: str) -> Path:
    path = Path(stored_path)
    if path.is_absolute():
        return path.resolve()
    root = Path(data_root).resolve()
    target = (root / path).resolve()
    if not target.is_relative_to(root):
        raise ValueError("La ruta relativa escapa de la raíz de datos.")
    return target
