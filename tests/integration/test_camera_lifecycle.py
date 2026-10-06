from threading import Event, get_ident

import numpy as np
import pytest
from PySide6.QtCore import QTimer

from blanquita_vision.application.recovery_policy import RecoveryPolicy
from blanquita_vision.domain.models.camera_state import CameraError, CameraState
from blanquita_vision.presentation.main_window import MainWindow
from tests.fixtures.fake_camera import FakeCamera, make_frame


def select_camera(controller, runner, wait_until):
    controller.refresh()
    wait_until(lambda: not runner.active)
    controller.select("0")


def start_stream(controller, runner, wait_until):
    select_camera(controller, runner, wait_until)
    controller.connect()
    wait_until(lambda: controller.runtime.state is CameraState.STREAMING
               and controller.runtime.last_frame_at is not None
               and controller.store.latest() is not None)


def test_tc_001_startup_tc_002_navigation(camera_setup, qapp):
    camera, store, runner, controller = camera_setup()
    window = MainWindow(controller, runner)
    window.showMaximized()
    qapp.processEvents()
    assert window.isMaximized()
    assert window.stack.currentIndex() == 0
    assert controller.runtime.state is CameraState.DISCONNECTED
    assert window.statusBar().currentMessage() == "Percepción local · Cámara desconectada"
    assert camera.open_calls == []
    assert not runner.active
    for index in range(7):
        window.sidebar.setCurrentRow(index)
        assert window.stack.currentIndex() == index
    window.close()


def test_tc_003_discovery_tc_005_selection_without_connection(camera_setup, wait_until):
    camera, store, runner, controller = camera_setup()
    select_camera(controller, runner, wait_until)
    assert [d.index for d in controller.devices] == [0, 2]
    assert camera.open_calls == []
    assert controller.runtime.selected_device.index == 0
    controller.select(None)
    assert controller.runtime.selected_device is None


def test_tc_004_empty_state(camera_setup, wait_until):
    camera, store, runner, controller = camera_setup(FakeCamera(indices=()))
    window = MainWindow(controller, runner)
    window.live.refresh_button.click()
    wait_until(lambda: not runner.active)
    assert "No se detectaron cámaras" in window.live.message.text()
    assert not window.live.connect_button.isEnabled()
    assert window.live.refresh_button.isEnabled()
    window.close()


def test_tc_006_connect_tc_009_effective_properties_tc_016_manual_stop(
    camera_setup, wait_until,
):
    camera, store, runner, controller = camera_setup()
    window = MainWindow(controller, runner)
    states = []
    controller.on_state.append(lambda runtime: states.append(runtime.state))
    start_stream(controller, runner, wait_until)
    assert CameraState.CONNECTING in states
    assert window.statusBar().currentMessage() == "Percepción local · Cámara conectada · Video en vivo"
    window.sidebar.setCurrentRow(4)
    assert "Cámara conectada" in window.statusBar().currentMessage()
    assert "16 × 12" in window.live.resolution_label.text()
    assert "25.0" in window.live.fps_label.text()
    assert window.live.disconnect_button.isEnabled()
    assert window.live.capture_button.isEnabled()
    assert not window.live.selector.isEnabled()
    assert not window.live.refresh_button.isEnabled()
    window.live.disconnect_button.click()
    wait_until(lambda: not runner.active)
    assert controller.runtime.state is CameraState.DISCONNECTED
    assert CameraState.STOPPING in states
    assert window.statusBar().currentMessage() == "Percepción local · Cámara desconectada"
    assert CameraState.RECOVERING not in states
    assert store.latest() is None
    assert not camera.is_open
    assert camera.close_calls >= 1
    window.close()


def test_tc_007_failed_open_and_tc_015_retry(camera_setup, wait_until):
    failure = CameraError("open_failed", "Apertura fallida de prueba.")
    camera, store, runner, controller = camera_setup(FakeCamera(open_errors=[failure]))
    window = MainWindow(controller, runner)
    select_camera(controller, runner, wait_until)
    controller.connect()
    wait_until(lambda: not runner.active)
    assert controller.runtime.state is CameraState.ERROR
    assert "Error de cámara" in window.statusBar().currentMessage()
    assert "Apertura fallida" in window.statusBar().currentMessage()
    assert window.live.retry_button.isEnabled()
    assert "Apertura fallida" in window.live.message.text()
    window.live.retry_button.click()
    wait_until(lambda: controller.runtime.state is CameraState.STREAMING)
    window.close()
    wait_until(lambda: not runner.active)


def test_first_frame_invalid_aborts_without_recovery(camera_setup, wait_until):
    camera, store, runner, controller = camera_setup(FakeCamera(reads=[None]))
    select_camera(controller, runner, wait_until)
    controller.connect()
    wait_until(lambda: not runner.active)
    assert controller.runtime.state is CameraState.ERROR
    assert controller.runtime.last_error.code == "first_frame_invalid"
    assert store.metrics().reconnect_attempts == 0
    assert store.latest() is None


def test_tc_011_isolated_invalid_frame_does_not_replace_latest(camera_setup, wait_until):
    camera, store, runner, controller = camera_setup(
        FakeCamera(reads=[make_frame(1), None, make_frame(2)], delay=0.01)
    )
    states = []
    controller.on_state.append(lambda runtime: states.append(runtime.state))
    start_stream(controller, runner, wait_until)
    wait_until(lambda: store.metrics().invalid_frames == 1 and camera.read_calls >= 3)
    assert CameraState.RECOVERING not in states
    assert store.latest() is not None


def test_tc_012_loss_tc_013_successful_recovery(camera_setup, wait_until):
    failure = CameraError("open_failed", "Indisponible temporalmente.")
    camera = FakeCamera(reads=[make_frame(), None, None, None],
                        open_errors=[None, failure, None])
    camera, store, runner, controller = camera_setup(camera)
    window = MainWindow(controller, runner)
    states = []
    footer_messages = []
    controller.on_state.append(lambda runtime: states.append(runtime.state))
    controller.on_state.append(lambda runtime: footer_messages.append(window.statusBar().currentMessage()))
    start_stream(controller, runner, wait_until)
    wait_until(lambda: len(camera.open_calls) == 3
               and controller.runtime.state is CameraState.STREAMING)
    assert CameraState.RECOVERING in states
    assert any("Recuperando conexión" in message for message in footer_messages)
    assert "Cámara conectada" in window.statusBar().currentMessage()
    assert store.metrics().reconnect_attempts == 2
    assert controller.runtime.properties.backend_name == "FAKE"
    window.close()
    wait_until(lambda: not runner.active)


def test_tc_014_exhaustion_is_bounded_and_error_can_refresh(camera_setup, wait_until):
    failure = CameraError("open_failed", "Cámara ausente.")
    fake = FakeCamera(reads=[make_frame(), None, None, None],
                      open_errors=[None, failure, failure, failure])
    camera, store, runner, controller = camera_setup(fake)
    select_camera(controller, runner, wait_until)
    controller.connect()
    wait_until(lambda: not runner.active)
    assert controller.runtime.state is CameraState.ERROR
    assert store.metrics().reconnect_attempts == 3
    assert len(camera.open_calls) == 4
    assert store.latest() is None
    controller.refresh()
    wait_until(lambda: not runner.active)
    assert controller.runtime.state is CameraState.DISCONNECTED


def test_disconnect_during_recovery_cancels_wait(camera_setup, wait_until):
    camera, store, runner, controller = camera_setup(
        FakeCamera(reads=[make_frame(), None, None, None]),
        RecoveryPolicy(3, 10.0, 3),
    )
    select_camera(controller, runner, wait_until)
    controller.connect()
    wait_until(lambda: controller.runtime.state is CameraState.RECOVERING)
    controller.disconnect()
    wait_until(lambda: not runner.active)
    assert controller.runtime.state is CameraState.DISCONNECTED
    assert store.metrics().reconnect_attempts == 0


def test_tc_017_ui_capture_independent_tc_018_unavailable(camera_setup, wait_until, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    camera, store, runner, controller = camera_setup()
    window = MainWindow(controller, runner)
    with pytest.raises(CameraError):
        controller.capture()
    start_stream(controller, runner, wait_until)
    window.live.capture_button.click()
    snapshot = window.live.last_capture
    assert snapshot is not None
    before = snapshot.image_copy.copy()
    wait_until(lambda: camera.read_calls >= 5)
    assert np.array_equal(snapshot.image_copy, before)
    assert not list(tmp_path.iterdir())
    window.close()
    wait_until(lambda: not runner.active)


def test_tc_019_shutdown_releases_worker(camera_setup, wait_until, qapp):
    camera, store, runner, controller = camera_setup()
    window = MainWindow(controller, runner)
    window.show()
    start_stream(controller, runner, wait_until)
    window.close()
    wait_until(lambda: not runner.active and not window.isVisible())
    assert not camera.is_open
    assert store.latest() is None
    assert controller.runtime.state is CameraState.DISCONNECTED


def test_operations_stay_off_ui_thread_and_ui_timer_runs(camera_setup, wait_until):
    camera, store, runner, controller = camera_setup(FakeCamera(delay=0.03))
    ticks = []
    timer = QTimer()
    timer.setInterval(5)
    timer.timeout.connect(lambda: ticks.append(1))
    timer.start()
    start_stream(controller, runner, wait_until)
    wait_until(lambda: camera.read_calls >= 5)
    timer.stop()
    assert len(ticks) >= 3
    assert all(thread != get_ident() for thread in camera.owner_threads)


@pytest.mark.parametrize("operation", ["discover", "connect"])
def test_cancel_blocked_operation_keeps_ui_open_until_release(
    operation, camera_setup, wait_until, qapp,
):
    entered, release = Event(), Event()

    class BlockingCamera(FakeCamera):
        def discover(self):
            if operation == "discover":
                entered.set()
                release.wait()
            return super().discover()

        def open(self, config):
            if operation == "connect":
                entered.set()
                release.wait()
            return super().open(config)

    camera, store, runner, controller = camera_setup(BlockingCamera())
    window = MainWindow(controller, runner, shutdown_timeout_ms=30)
    window.show()
    try:
        if operation == "connect":
            select_camera(controller, runner, wait_until)
            controller.connect()
        else:
            controller.refresh()
        wait_until(entered.is_set)
        assert window.live.disconnect_button.isEnabled()
        window.close()
        wait_until(lambda: "driver de cámara sigue bloqueado" in window.statusBar().currentMessage())
        assert window.isVisible()
        assert controller.runtime.state is CameraState.STOPPING
        release.set()
        wait_until(lambda: not runner.active and not window.isVisible())
        assert controller.runtime.state is CameraState.DISCONNECTED
        assert store.latest() is None
    finally:
        release.set()
        controller.disconnect()
        wait_until(lambda: not runner.active)
        window.close()


def test_refresh_preserves_only_still_available_selection(camera_setup, wait_until):
    camera, store, runner, controller = camera_setup()
    select_camera(controller, runner, wait_until)
    controller.refresh()
    wait_until(lambda: not runner.active)
    assert controller.runtime.selected_device.index == 0
    camera.devices = []
    controller.refresh()
    wait_until(lambda: not runner.active)
    assert controller.runtime.selected_device is None


def test_worker_exception_is_reported_and_released(camera_setup, wait_until):
    camera, store, runner, controller = camera_setup(
        FakeCamera(reads=[make_frame(), RuntimeError("fallo inesperado")])
    )
    select_camera(controller, runner, wait_until)
    controller.connect()
    wait_until(lambda: not runner.active)
    assert controller.runtime.state is CameraState.ERROR
    assert controller.runtime.last_error.code == "worker_failed"
    assert not camera.is_open
