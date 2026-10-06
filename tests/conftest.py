import os
from time import monotonic

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("PYQTGRAPH_QT_LIB", "PySide6")

import pytest
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from blanquita_vision.application.camera_controller import CameraController
from blanquita_vision.application.latest_frame_store import LatestFrameStore
from blanquita_vision.application.recovery_policy import RecoveryPolicy
from blanquita_vision.presentation.theme import THEME
from blanquita_vision.presentation.workers.camera_worker import QtCameraRunner
from tests.fixtures.fake_camera import FakeCamera


def pytest_addoption(parser):
    parser.addoption("--hardware-camera-index", type=int, default=None,
                     help="Índice explícito para la prueba opcional con cámara real.")


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    app.setStyle("Fusion")
    app.setStyleSheet(THEME)
    yield app


@pytest.fixture
def wait_until(qapp):
    def wait(predicate, timeout=3.0):
        deadline = monotonic() + timeout
        while not predicate() and monotonic() < deadline:
            qapp.processEvents()
            QTest.qWait(5)
        qapp.processEvents()
        assert predicate(), "La condición no se cumplió dentro del plazo de prueba."
    return wait


@pytest.fixture
def camera_setup(qapp, wait_until):
    resources = []

    def create(camera=None, policy=None):
        camera = camera or FakeCamera()
        store = LatestFrameStore()

        def factory(cancellation):
            camera.cancellation = cancellation
            return camera

        runner = QtCameraRunner(factory, store, policy or RecoveryPolicy(3, 0.01, 3))
        controller = CameraController(runner, store)
        resources.append((controller, runner))
        return camera, store, runner, controller

    yield create
    for controller, runner in resources:
        controller.disconnect()
        wait_until(lambda: not runner.active)
        runner.deleteLater()
    qapp.processEvents()


@pytest.fixture
def vision_setup(camera_setup, wait_until):
    from blanquita_vision.adapters.calibration.in_memory_calibration_repository import InMemoryCalibrationRepository
    from blanquita_vision.adapters.calibration.opencv_homography_solver import OpenCvHomographySolver
    from blanquita_vision.adapters.position.homography_position_estimator import HomographyPositionEstimator
    from blanquita_vision.application.calibration_service import CalibrationService
    from blanquita_vision.application.vision_pipeline_controller import VisionPipelineController
    from blanquita_vision.presentation.workers.vision_worker import QtVisionRunner
    from tests.fixtures.vision_fakes import ColorCamera, FakeDetector, FakeTracker

    resources = []

    def create(detector=None, tracker=None):
        camera, store, camera_runner, camera_controller = camera_setup(ColorCamera())
        detector, tracker = detector or FakeDetector(), tracker or FakeTracker()
        calibration = CalibrationService(InMemoryCalibrationRepository(), OpenCvHomographySolver())
        runner = QtVisionRunner(store, lambda: detector, lambda: tracker, HomographyPositionEstimator)
        vision = VisionPipelineController(camera_controller, runner, calibration)
        resources.append(vision)
        return camera, camera_controller, camera_runner, vision, calibration, detector, tracker

    yield create
    for vision in resources:
        vision.stop()
        wait_until(lambda: not vision.runner.active)
        vision.dispose()
        vision.runner.deleteLater()


@pytest.fixture
def operational_setup(vision_setup, wait_until, tmp_path):
    from blanquita_vision.adapters.network.websocket_vision_server import WebSocketVisionServer
    from blanquita_vision.adapters.storage.sqlite_calibration_repository import SQLiteCalibrationRepository
    from blanquita_vision.adapters.storage.sqlite_vision_repository import SQLiteVisionRepository
    from blanquita_vision.adapters.system_diagnostics_provider import SystemDiagnosticsProvider
    from blanquita_vision.application.operations_service import OperationsService
    from blanquita_vision.presentation.workers.network_worker import QtNetworkController
    from blanquita_vision.presentation.workers.operations_controller import QtOperationsController
    from blanquita_vision.presentation.workers.storage_worker import QtStorageController
    resources = []

    def create(data_root=None, repository_factory=SQLiteVisionRepository, expect_storage="READY"):
        device, camera, runner, vision, calibration, detector, tracker = vision_setup()
        root = data_root or tmp_path / str(len(resources))
        storage = QtStorageController(root, repository_factory=repository_factory)
        repo = SQLiteCalibrationRepository(storage)
        calibration.repository = repo
        network = QtNetworkController(WebSocketVisionServer("127.0.0.1", 0))
        service = OperationsService(camera, vision, calibration, storage, network, repo,
                                    SystemDiagnosticsProvider().snapshot())
        operations = QtOperationsController(service)
        resources.append((operations, camera, runner, vision))
        operations.start()
        wait_until(lambda: storage.health["state"] == expect_storage and network.server.health()["state"] == "LISTENING")
        return device, camera, runner, vision, calibration, operations

    yield create
    for operations, camera, runner, vision in resources:
        operations.shutdown()
        vision.stop()
        camera.disconnect()
        wait_until(lambda: not runner.active and not vision.runner.active and not operations.service.network.active)
        operations.finish_storage()
        wait_until(lambda: not operations.active, timeout=10)
        operations.dispose()
        operations.deleteLater()
