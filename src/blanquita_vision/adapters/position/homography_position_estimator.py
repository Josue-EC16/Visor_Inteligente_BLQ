from math import hypot, isfinite
from sys import float_info

from ...domain.models.calibration import Calibration, CalibrationStatus
from ...domain.models.geometry import ImagePoint
from ...domain.models.position import SpatialPosition


class HomographyPositionEstimator:
    def estimate(self, image_point: ImagePoint, calibration: Calibration) -> SpatialPosition:
        if calibration.status is not CalibrationStatus.VALID:
            raise ValueError("No existe calibración válida.")
        vector = (image_point.u, image_point.v, 1.0)
        values = [sum(a * b for a, b in zip(row, vector)) for row in calibration.homography]
        denominator = values[2]
        bound = hypot(*calibration.homography[2]) * hypot(*vector)
        if not isfinite(denominator) or abs(denominator) <= float_info.epsilon * bound:
            raise ValueError("Denominador homogéneo inválido.")
        x, y = values[0] / denominator, values[1] / denominator
        if not isfinite(x) or not isfinite(y):
            raise ValueError("Coordenadas físicas no finitas.")
        return SpatialPosition(x, y, None, calibration.unit)
