from itertools import combinations

import cv2
import numpy as np

from ...domain.models.calibration import CalibrationPoint, Matrix3x3


class OpenCvHomographySolver:
    @staticmethod
    def _validate_geometry(points: np.ndarray) -> None:
        if not np.isfinite(points).all() or len(np.unique(points, axis=0)) != 4:
            raise ValueError("Los cuatro puntos deben ser distintos y finitos.")
        scale = np.ptp(points, axis=0).max()
        if scale == 0:
            raise ValueError("Puntos degenerados.")
        normalized = (points - points.mean(axis=0)) / scale
        for triangle in combinations(normalized, 3):
            matrix = np.column_stack((np.asarray(triangle), np.ones(3)))
            if np.linalg.matrix_rank(matrix) < 3:
                raise ValueError("Calibración degenerada: tres puntos son colineales.")

    def solve(self, points: tuple[CalibrationPoint, ...]) -> tuple[Matrix3x3, float]:
        if len(points) != 4:
            raise ValueError("Se requieren exactamente cuatro correspondencias.")
        if len({p.physical.unit for p in points}) != 1:
            raise ValueError("Las unidades físicas no coinciden.")
        source = np.asarray([(p.image.u, p.image.v) for p in points], dtype=np.float64)
        target = np.asarray([(p.physical.x, p.physical.y) for p in points], dtype=np.float64)
        self._validate_geometry(source)
        self._validate_geometry(target)
        matrix, _ = cv2.findHomography(source, target, method=0)
        if matrix is None or not np.isfinite(matrix).all():
            raise ValueError("No se obtuvo una homografía finita.")
        scale = np.max(np.abs(matrix))
        if scale == 0 or np.linalg.matrix_rank(matrix / scale) < 3:
            raise ValueError("Homografía singular.")
        matrix = matrix / scale
        homogeneous = np.column_stack((source, np.ones(4))) @ matrix.T
        bound = np.linalg.norm(matrix[2]) * np.linalg.norm(np.column_stack((source, np.ones(4))), axis=1)
        if np.any(np.abs(homogeneous[:, 2]) <= np.finfo(float).eps * bound):
            raise ValueError("La transformación tiene un denominador inválido.")
        mapped = homogeneous[:, :2] / homogeneous[:, 2, None]
        error = float(np.mean(np.linalg.norm(mapped - target, axis=1)))
        if not np.isfinite(error):
            raise ValueError("Error de reproyección no finito.")
        return tuple(tuple(float(v) for v in row) for row in matrix), error
