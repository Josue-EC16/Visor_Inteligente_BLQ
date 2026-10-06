"""Arranque: uv run --locked src/blanquita_vision/main.py."""

import argparse
import logging
import sys
from pathlib import Path

# Permite ejecutar el src-layout sin un backend de empaquetado adicional.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtWidgets import QApplication

from blanquita_vision.adapters.camera.opencv_camera import OpenCvCamera
from blanquita_vision.adapters.storage.sqlite_calibration_repository import SQLiteCalibrationRepository
from blanquita_vision.adapters.calibration.opencv_homography_solver import OpenCvHomographySolver
from blanquita_vision.adapters.detection.csrt_tracker import CsrtTracker
from blanquita_vision.adapters.detection.opencv_hook_detector import OpenCvHookDetector
from blanquita_vision.adapters.position.homography_position_estimator import HomographyPositionEstimator
from blanquita_vision.application.calibration_service import CalibrationService
from blanquita_vision.application.camera_controller import CameraController
from blanquita_vision.application.latest_frame_store import LatestFrameStore
from blanquita_vision.application.vision_pipeline_controller import VisionPipelineController
from blanquita_vision.application.operations_service import OperationsService
from blanquita_vision.adapters.network.websocket_vision_server import WebSocketVisionServer
from blanquita_vision.adapters.network.udp_discovery_responder import UdpDiscoveryResponder
from blanquita_vision.adapters.system_diagnostics_provider import SystemDiagnosticsProvider
from blanquita_vision.infrastructure.config import AppConfig
from blanquita_vision.infrastructure.logging import configure_logging
from blanquita_vision.presentation.main_window import MainWindow
from blanquita_vision.presentation.theme import THEME
from blanquita_vision.presentation.workers.camera_worker import QtCameraRunner
from blanquita_vision.presentation.workers.vision_worker import QtVisionRunner
from blanquita_vision.presentation.workers.storage_worker import QtStorageController
from blanquita_vision.presentation.workers.network_worker import QtNetworkController
from blanquita_vision.presentation.workers.operations_controller import QtOperationsController
from blanquita_vision.presentation.workers.discovery_worker import QtDiscoveryController


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BLANQUITA Vision — captura local")
    parser.add_argument("--backend", default="AUTO",
                        help="Backend OpenCV: AUTO por defecto; identificador CAP_* sin prefijo.")
    parser.add_argument("--data-dir", default=str(Path(__file__).resolve().parents[2] / "data"),
                        help="Raíz de datos SQLite y capturas; predeterminada: data del proyecto.")
    args = parser.parse_args(argv)
    configure_logging()
    config = AppConfig(backend=args.backend.upper())
    try:
        OpenCvCamera.backend_id(config.backend)
    except Exception as exc:
        parser.error(str(exc))
    app = QApplication([sys.argv[0]])
    app.setApplicationName("BLANQUITA Vision")
    app.setStyle("Fusion")
    app.setStyleSheet(THEME)
    store = LatestFrameStore()
    runner = QtCameraRunner(
        lambda cancellation: OpenCvCamera(
            config.discovery_indices, config.backend, cancellation=cancellation,
        ), store,
    )
    controller = CameraController(runner, store, config.backend)
    storage = QtStorageController(Path(args.data_dir))
    repository = SQLiteCalibrationRepository(storage)
    calibration = CalibrationService(repository, OpenCvHomographySolver())
    vision_runner = QtVisionRunner(store, OpenCvHookDetector, CsrtTracker, HomographyPositionEstimator)
    vision = VisionPipelineController(controller, vision_runner, calibration)
    network = QtNetworkController(WebSocketVisionServer())
    discovery = QtDiscoveryController(UdpDiscoveryResponder(network.server.health))
    service = OperationsService(controller, vision, calibration, storage, network, repository,
                                SystemDiagnosticsProvider().snapshot(), discovery=discovery)
    operations = QtOperationsController(service)
    window = MainWindow(controller, runner, config.shutdown_timeout_ms, vision, calibration, operations)
    operations.start()
    window.showMaximized()
    logging.getLogger(__name__).info("application_started")
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
