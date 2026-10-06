from dataclasses import replace

import pytest

from blanquita_vision.adapters.calibration.in_memory_calibration_repository import InMemoryCalibrationRepository
from blanquita_vision.adapters.calibration.opencv_homography_solver import OpenCvHomographySolver
from blanquita_vision.adapters.position.homography_position_estimator import HomographyPositionEstimator
from blanquita_vision.application.accuracy_metrics import AccuracyAccumulator
from blanquita_vision.application.calibration_service import CalibrationService
from blanquita_vision.application.position_filter import EmaPositionFilter
from blanquita_vision.domain.models.calibration import CalibrationPoint, CalibrationStatus
from blanquita_vision.domain.models.geometry import ImagePoint, PhysicalPoint2D
from blanquita_vision.domain.models.position import SpatialPosition


def calibration_points():
    return tuple(CalibrationPoint(ImagePoint(u, v), PhysicalPoint2D(2 * u + 10, 400 - 3 * v, "mm"))
                 for u, v in ((0, 0), (159, 0), (159, 119), (0, 119)))


def calibrated_service():
    service = CalibrationService(InMemoryCalibrationRepository(), OpenCvHomographySolver())
    service.observe_geometry("0", 160, 120)
    calibration = service.compute(calibration_points(), "0", 160, 120)
    service.apply(calibration)
    return service, calibration


def test_tc_01_013_016_017_known_homography_and_vertical_y():
    service, calibration = calibrated_service()
    assert service.status is CalibrationStatus.VALID
    position = HomographyPositionEstimator().estimate(ImagePoint(55, 50), calibration)
    assert position.x == pytest.approx(120, abs=1e-5)
    assert position.y == pytest.approx(250, abs=1e-5)
    assert position.z is None
    assert position.unit == "mm"
    assert calibration.internal_reprojection_error < 1e-5


def test_tc_01_014_repeated_points_rejected():
    points = calibration_points()
    with pytest.raises(ValueError, match="distintos"):
        OpenCvHomographySolver().solve((points[0], points[0], points[2], points[3]))


def test_tc_01_015_three_collinear_points_rejected():
    points = tuple(CalibrationPoint(ImagePoint(u, v), PhysicalPoint2D(u, v, "mm"))
                   for u, v in ((0, 0), (10, 10), (20, 20), (0, 20)))
    with pytest.raises(ValueError, match="colineales"):
        OpenCvHomographySolver().solve(points)


def test_calibration_rejects_inconsistent_units_and_missing_points():
    service, calibration = calibrated_service()
    points = calibration_points()
    with pytest.raises(ValueError):
        service.compute(points[:3], "0", 160, 120)
    mixed = (*points[:3], replace(points[3], physical=PhysicalPoint2D(0, 20, "cm")))
    with pytest.raises(ValueError, match="unidades"):
        service.compute(mixed, "0", 160, 120)


@pytest.mark.parametrize("geometry", [("1", 160, 120), ("0", 320, 240)])
def test_tc_01_019_020_geometry_invalidates(geometry):
    service, calibration = calibrated_service()
    service.observe_geometry(*geometry)
    assert service.status is CalibrationStatus.INVALID
    assert service.active() is None
    assert service.repository.get_active().status is CalibrationStatus.INVALID


def test_tc_01_021_reconnection_equivalent_preserves_calibration():
    service, calibration = calibrated_service()
    service.observe_geometry("0", None, None)
    service.observe_geometry("0", 160, 120)
    assert service.active() == calibration


def test_tc_01_022_manual_invalidation_and_late_candidate_rejected():
    service, calibration = calibrated_service()
    service.invalidate()
    with pytest.raises(ValueError):
        HomographyPositionEstimator().estimate(ImagePoint(55, 50), service.repository.get_active())
    service.observe_geometry("1", 160, 120)
    with pytest.raises(ValueError, match="cambiaron"):
        service.apply(calibration)


def test_homogeneous_zero_denominator_rejected():
    service, calibration = calibrated_service()
    broken = replace(calibration, homography=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 0.0)))
    with pytest.raises(ValueError, match="Denominador"):
        HomographyPositionEstimator().estimate(ImagePoint(1, 1), broken)


def test_tc_01_023_024_026_ema_preserves_raw_and_resets():
    filter_ = EmaPositionFilter(0.5)
    first = SpatialPosition(10, 20, None, "mm")
    assert filter_.update(first) == first
    raw = SpatialPosition(20, 40, None, "mm")
    assert filter_.update(raw) == SpatialPosition(15, 30, None, "mm")
    assert raw.x == 20
    filter_.reset()
    assert filter_.update(raw) == raw
    assert filter_.update(SpatialPosition()) == SpatialPosition()
    assert filter_.update(first) == first


@pytest.mark.parametrize("alpha", [0, -1, 1.01, float("nan"), float("inf")])
def test_tc_01_025_invalid_alpha(alpha):
    with pytest.raises(ValueError):
        EmaPositionFilter(alpha)


def test_accuracy_summary_uses_independent_reference_errors():
    accumulator = AccuracyAccumulator()
    result = accumulator.add(SpatialPosition(13, 24, None, "mm"), PhysicalPoint2D(10, 20, "mm"))
    assert (result.mae_x, result.mae_y, result.mean_2d_error, result.maximum_2d_error) == (3, 4, 5, 5)
    result = accumulator.add(SpatialPosition(10, 20, None, "mm"), PhysicalPoint2D(10, 20, "mm"))
    assert result.count == 2
    assert result.mean_2d_error == 2.5
    assert result.maximum_2d_error == 5
    with pytest.raises(ValueError):
        accumulator.add(SpatialPosition(), PhysicalPoint2D(0, 0, "mm"))
