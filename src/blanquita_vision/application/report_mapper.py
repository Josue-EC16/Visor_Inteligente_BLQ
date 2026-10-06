from dataclasses import replace

from ..domain.models.calibration import Calibration
from ..domain.models.protocol import PositionPayload, ReportPayload, message
from ..domain.models.vision_observation import VisionObservation


def millimeter_factor(unit: str | None) -> float:
    factors = {"mm": 1.0, "cm": 10.0, "m": 1000.0}
    if unit not in factors:
        raise ValueError("Unidad no admitida: se requieren mm, cm o m.")
    return factors[unit]


def calibration_in_mm(calibration: Calibration) -> Calibration:
    factor = millimeter_factor(calibration.unit)
    points = tuple(replace(point, physical=replace(point.physical,
                                                  x=point.physical.x * factor,
                                                  y=point.physical.y * factor, unit="mm"))
                   for point in calibration.points)
    matrix = tuple(tuple(value * factor if row < 2 else value for value in values)
                   for row, values in enumerate(calibration.homography))
    error = calibration.internal_reprojection_error
    return replace(calibration, unit="mm", points=points, homography=matrix,
                   internal_reprojection_error=error * factor if error is not None else None)


def report_from_observation(observation: VisionObservation):
    detected = observation.detection is not None and observation.detection.detected
    position = PositionPayload()
    estimate = observation.position
    if detected and observation.calibration_status.value == "VALID" and estimate is not None and estimate.calibrated:
        source = estimate.filtered_position
        if source.x is not None and source.y is not None:
            factor = millimeter_factor(source.unit)
            position = PositionPayload(x=source.x * factor, y=source.y * factor)
    payload = ReportPayload(
        detected=detected, position=position,
        confidence=observation.detection.confidence if observation.detection else 0.0,
        calibrationStatus=observation.calibration_status.value,
        trackingState=observation.tracking.state.value if observation.tracking else "INACTIVE",
        frameSequence=observation.frame_sequence, observationTimestamp=observation.timestamp,
    )
    return message("vision.report", payload)
