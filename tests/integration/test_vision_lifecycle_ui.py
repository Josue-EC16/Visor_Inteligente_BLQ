from threading import Event, get_ident
from time import sleep

import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QLabel

from blanquita_vision.adapters.detection.opencv_hook_detector import OpenCvHookDetector
from blanquita_vision.domain.models.camera_state import CameraState
from blanquita_vision.domain.models.calibration import CalibrationStatus
from blanquita_vision.domain.models.vision_observation import VisionPipelineState
from blanquita_vision.presentation.main_window import MainWindow
from tests.fixtures.vision_fakes import FakeDetector, test_parameters as parameters
from tests.integration.test_camera_lifecycle import select_camera, start_stream
from tests.unit.test_calibration_position_filter import calibration_points


def configure_and_start(camera, camera_runner, vision, wait_until):
    start_stream(camera, camera_runner, wait_until)
    vision.configure(parameters(), 0.5)
    vision.start()
    wait_until(lambda: vision.last_result is not None)


def test_tc_01_001_requires_camera_and_explicit_parameters(vision_setup, wait_until):
    device, camera, runner, vision, service, detector, tracker = vision_setup()
    with pytest.raises(ValueError, match="cámara"):
        vision.start()
    start_stream(camera, runner, wait_until)
    with pytest.raises(ValueError, match="HSV"):
        vision.start()
    assert vision.state is VisionPipelineState.STOPPED


def test_tc_01_002_003_manual_start_stop_and_no_more_processing(vision_setup, wait_until):
    device, camera, runner, vision, service, detector, tracker = vision_setup()
    states = []
    vision.on_state.append(lambda: states.append(vision.state))
    configure_and_start(camera, runner, vision, wait_until)
    assert VisionPipelineState.STARTING in states
    assert vision.state is VisionPipelineState.RUNNING
    vision.stop()
    wait_until(lambda: not vision.runner.active)
    calls = detector.calls
    sleep(0.03)
    assert detector.calls == calls
    assert camera.runtime.state is CameraState.STREAMING
    assert device.is_open
    assert vision.last_result is None
    assert vision.state is VisionPipelineState.STOPPED
    assert all(thread != get_ident() for thread in detector.threads)


def test_camera_disconnect_stops_vision_and_reconnect_needs_manual_start(vision_setup, wait_until):
    device, camera, runner, vision, service, detector, tracker = vision_setup()
    configure_and_start(camera, runner, vision, wait_until)
    camera.disconnect()
    wait_until(lambda: not vision.runner.active and not runner.active)
    assert vision.last_result is None
    camera.connect()
    wait_until(lambda: camera.runtime.state is CameraState.STREAMING)
    assert not vision.runner.active
    assert vision.state is VisionPipelineState.STOPPED


def test_parameter_changes_restart_and_drop_previous_observation(vision_setup, wait_until):
    device, camera, runner, vision, service, detector, tracker = vision_setup()
    configure_and_start(camera, runner, vision, wait_until)
    initializations = tracker.initializations
    vision.configure(parameters(min_area=25), 0.7)
    assert vision.last_result is None
    wait_until(lambda: vision.last_result is not None and tracker.initializations > initializations)
    assert vision.alpha == 0.7
    assert vision.parameters.min_area == 25


def test_tc_01_019_020_021_022_calibration_lifecycle_with_camera(vision_setup, wait_until):
    device, camera, runner, vision, service, detector, tracker = vision_setup()
    start_stream(camera, runner, wait_until)
    calibration = service.compute(calibration_points(), "0", 160, 120)
    service.apply(calibration)
    camera.disconnect()
    wait_until(lambda: not runner.active)
    camera.connect()
    wait_until(lambda: camera.runtime.state is CameraState.STREAMING)
    assert service.active() == calibration
    service.observe_geometry("0", 320, 240)
    assert service.active() is None
    assert service.status is CalibrationStatus.INVALID
    service.observe_geometry("0", 160, 120)
    service.apply(calibration)
    camera.disconnect()
    wait_until(lambda: not runner.active)
    camera.select("2")
    assert service.status is CalibrationStatus.INVALID


def test_calibration_change_discards_physical_position_and_restarts(vision_setup, wait_until):
    device, camera, runner, vision, service, detector, tracker = vision_setup()
    configure_and_start(camera, runner, vision, wait_until)
    candidate = service.compute(calibration_points(), "0", 160, 120)
    service.apply(candidate)
    wait_until(lambda: vision.last_result is not None and vision.last_result.observation.position is not None)
    assert vision.last_result.observation.position.raw_position.z is None
    service.invalidate()
    assert vision.last_result is None
    wait_until(lambda: vision.last_result is not None)
    assert vision.last_result.observation.position is None


def test_tc_01_027_slow_vision_skips_frames_without_starving_preview(vision_setup, wait_until):
    entered, release = Event(), Event()
    class SlowDetector(FakeDetector):
        def detect(self, frame, parameters):
            if self.calls == 0:
                entered.set()
                release.wait()
            return super().detect(frame, parameters)
    device, camera, runner, vision, service, detector, tracker = vision_setup(SlowDetector())
    try:
        start_stream(camera, runner, wait_until)
        vision.configure(parameters(), 0.5)
        vision.start()
        wait_until(entered.is_set)
        initial = device.read_calls
        wait_until(lambda: device.read_calls >= initial + 10)
        release.set()
        wait_until(lambda: vision.last_result is not None and vision.last_result.metrics.frames_processed >= 4)
        assert vision.last_result.metrics.skipped_frames > 0
        assert camera.store.latest().sequence >= vision.last_result.frame.sequence
        assert device.read_calls > detector.calls
    finally:
        release.set()


def test_tc_01_028_detector_error_keeps_camera_and_ui_available(vision_setup, wait_until):
    class FailingDetector(FakeDetector):
        def detect(self, frame, parameters):
            raise RuntimeError("Error de detector de prueba")
    device, camera, runner, vision, service, detector, tracker = vision_setup(FailingDetector())
    start_stream(camera, runner, wait_until)
    vision.configure(parameters(), 0.5)
    vision.start()
    wait_until(lambda: not vision.runner.active)
    assert vision.state is VisionPipelineState.ERROR
    assert "Error de detector" in vision.last_error
    assert camera.runtime.state is CameraState.STREAMING
    assert device.is_open
    vision.stop()
    assert vision.state is VisionPipelineState.STOPPED


def test_live_overlays_match_processed_frame_and_clear_on_stop(vision_setup, wait_until):
    device, camera, runner, vision, service, detector, tracker = vision_setup()
    window = MainWindow(camera, runner, vision=vision, calibration=service)
    try:
        configure_and_start(camera, runner, vision, wait_until)
        assert window.live.last_processed_sequence == vision.last_result.observation.frame_sequence
        assert window.live.video.box_item.isVisible()
        assert "Calidad" in window.live.vision_label.text()
        assert "No disponibles" in window.live.vision_label.text()
        vision.stop()
        wait_until(lambda: not vision.runner.active)
        assert not window.live.video.box_item.isVisible()
        assert window.live.last_processed_sequence is None
    finally:
        window.close()
        wait_until(lambda: not runner.active and not vision.runner.active)


def test_detection_controls_require_explicit_values_and_apply(vision_setup, wait_until):
    device, camera, runner, vision, service, detector, tracker = vision_setup()
    window = MainWindow(camera, runner, vision=vision, calibration=service)
    try:
        screen = window.detection_screen
        assert all(not field.text() for field in screen.fields.values())
        screen.start_button.click()
        assert not vision.runner.active
        assert "número válido" in screen.message.text()
        start_stream(camera, runner, wait_until)
        values = parameters()
        for name in ("hue_min", "hue_max", "saturation_min", "saturation_max", "value_min", "value_max",
                     "min_area", "minimum_confidence"):
            screen.fields[name].setText(str(getattr(values, name)))
        screen.fields["alpha"].setText("0.5")
        screen.start_button.click()
        wait_until(lambda: vision.last_result is not None)
        assert "Calidad actual" in screen.result_label.text()
        assert any("No es probabilidad" in label.text() for label in screen.findChildren(QLabel))
    finally:
        window.close()
        wait_until(lambda: not runner.active and not vision.runner.active)


def test_calibration_screen_four_points_async_apply_and_independent_error(vision_setup, wait_until):
    device, camera, runner, vision, service, detector, tracker = vision_setup()
    window = MainWindow(camera, runner, vision=vision, calibration=service)
    screen = window.calibration_screen
    try:
        start_stream(camera, runner, wait_until)
        screen.take_reference()
        assert screen.reference is not camera.store.latest()
        screen.unit.setText("mm")
        for row, point in enumerate(calibration_points()):
            screen.set_image_point(row, point.image)
            screen.table.item(row, 3).setText(str(point.physical.x))
            screen.table.item(row, 4).setText(str(point.physical.y))
        screen.calculate()
        wait_until(lambda: not screen.busy)
        assert screen.candidate is not None
        assert "No equivale a precisión física" in screen.message.text()
        screen.apply_candidate()
        assert service.status is CalibrationStatus.VALID
        vision.configure(parameters(), 0.5)
        vision.start()
        wait_until(lambda: vision.last_result is not None and vision.last_result.observation.position is not None)
        screen.accuracy.x.setText("120")
        screen.accuracy.y.setText("250")
        screen.accuracy.measure_button.click()
        assert "MAE X=" in screen.accuracy.summary.text()
        assert screen.accuracy.raw.count == 1
        screen.invalidate()
        assert screen.accuracy.raw.count == 0
        assert service.status is CalibrationStatus.INVALID
        assert vision.last_result is None
    finally:
        window.close()
        wait_until(lambda: not runner.active and not vision.runner.active and not screen.busy)


def test_shutdown_waits_for_vision_worker_and_drops_late_result(vision_setup, wait_until):
    entered, release = Event(), Event()
    class BlockedDetector(FakeDetector):
        def detect(self, frame, parameters):
            entered.set()
            release.wait()
            return super().detect(frame, parameters)
    device, camera, runner, vision, service, detector, tracker = vision_setup(BlockedDetector())
    window = MainWindow(camera, runner, shutdown_timeout_ms=30, vision=vision, calibration=service)
    window.show()
    try:
        start_stream(camera, runner, wait_until)
        vision.configure(parameters(), 0.5)
        vision.start()
        wait_until(entered.is_set)
        window.close()
        wait_until(lambda: "visión/calibración sigue activa" in window.statusBar().currentMessage())
        assert window.isVisible()
        release.set()
        wait_until(lambda: not vision.runner.active and not runner.active and not window.isVisible())
        assert vision.last_result is None
    finally:
        release.set()
        vision.stop()
        camera.disconnect()
        wait_until(lambda: not vision.runner.active and not runner.active)
        window.close()


def test_actual_opencv_detector_and_csrt_end_to_end(camera_setup, wait_until):
    from blanquita_vision.adapters.calibration.in_memory_calibration_repository import InMemoryCalibrationRepository
    from blanquita_vision.adapters.calibration.opencv_homography_solver import OpenCvHomographySolver
    from blanquita_vision.adapters.detection.csrt_tracker import CsrtTracker
    from blanquita_vision.adapters.position.homography_position_estimator import HomographyPositionEstimator
    from blanquita_vision.application.calibration_service import CalibrationService
    from blanquita_vision.application.vision_pipeline_controller import VisionPipelineController
    from blanquita_vision.presentation.workers.vision_worker import QtVisionRunner
    from tests.fixtures.vision_fakes import ColorCamera
    device, store, runner, camera = camera_setup(ColorCamera())
    service = CalibrationService(InMemoryCalibrationRepository(), OpenCvHomographySolver())
    vision_runner = QtVisionRunner(store, OpenCvHookDetector, CsrtTracker, HomographyPositionEstimator)
    vision = VisionPipelineController(camera, vision_runner, service)
    try:
        configure_and_start(camera, runner, vision, wait_until)
        wait_until(lambda: vision.last_result.metrics.frames_processed >= 3)
        assert vision.last_result.observation.detection.detected
        assert vision.last_result.observation.tracking.source == "csrt"
        assert vision.last_result.metrics.preprocess_ms is not None
    finally:
        vision.stop()
        wait_until(lambda: not vision_runner.active)
        vision.dispose()
        vision_runner.deleteLater()


def test_calibration_click_maps_scaled_image_to_source_pixels(vision_setup, wait_until, qapp):
    device, camera, runner, vision, service, detector, tracker = vision_setup()
    window = MainWindow(camera, runner, vision=vision, calibration=service)
    screen = window.calibration_screen
    window.showMaximized()
    window.sidebar.setCurrentRow(1)
    try:
        start_stream(camera, runner, wait_until)
        screen.take_reference()
        qapp.processEvents()
        scene_point = screen.video.image_item.mapToScene(QPointF(37, 53))
        viewport_point = screen.video.mapFromScene(scene_point)
        QTest.mouseClick(screen.video.viewport(), Qt.MouseButton.LeftButton, pos=viewport_point)
        assert float(screen.table.item(0, 1).text()) == pytest.approx(37, abs=1)
        assert float(screen.table.item(0, 2).text()) == pytest.approx(53, abs=1)
        assert screen.table.currentRow() == 1
    finally:
        window.close()
        wait_until(lambda: not runner.active and not vision.runner.active and not screen.busy)


def test_shutdown_waits_for_calibration_and_discards_candidate(vision_setup, wait_until):
    entered, release = Event(), Event()
    device, camera, runner, vision, service, detector, tracker = vision_setup()
    original_solver = service.solver
    class BlockingSolver:
        def solve(self, points):
            entered.set()
            release.wait()
            return original_solver.solve(points)
    service.solver = BlockingSolver()
    window = MainWindow(camera, runner, shutdown_timeout_ms=30, vision=vision, calibration=service)
    screen = window.calibration_screen
    window.show()
    try:
        start_stream(camera, runner, wait_until)
        screen.take_reference()
        screen.unit.setText("mm")
        for row, point in enumerate(calibration_points()):
            screen.set_image_point(row, point.image)
            screen.table.item(row, 3).setText(str(point.physical.x))
            screen.table.item(row, 4).setText(str(point.physical.y))
        screen.calculate()
        wait_until(entered.is_set)
        window.close()
        wait_until(lambda: "visión/calibración sigue activa" in window.statusBar().currentMessage())
        assert window.isVisible()
        release.set()
        wait_until(lambda: not screen.busy and not runner.active and not window.isVisible())
        assert screen.candidate is None
    finally:
        release.set()
        vision.stop()
        camera.disconnect()
        wait_until(lambda: not screen.busy and not runner.active and not vision.runner.active)
        window.close()
