import logging

from PySide6.QtCore import QTimer, Slot
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QHBoxLayout, QListWidget, QMainWindow, QStackedWidget, QWidget,
)

from ..application.camera_controller import CameraController
from ..domain.models.camera_state import CameraRuntimeState, CameraState
from .screens.analytics_screen import AnalyticsScreen
from .screens.calibration_screen import CalibrationScreen
from .screens.detection_screen import DetectionScreen
from .screens.diagnostics_screen import DiagnosticsScreen
from .screens.live_screen import LiveScreen
from .screens.reports_screen import ReportsScreen
from .screens.settings_screen import SettingsScreen

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self, controller: CameraController, runner,
                 shutdown_timeout_ms: int = 5000, vision=None, calibration=None, operations=None) -> None:
        super().__init__()
        self.controller = controller
        self.runner = runner
        self.vision = vision
        self.operations = operations
        self.setWindowTitle("BLANQUITA Vision")
        self._closing = False
        self.shutdown_timer = QTimer(self)
        self.shutdown_timer.setSingleShot(True)
        self.shutdown_timer.setInterval(shutdown_timeout_ms)
        self.shutdown_timer.timeout.connect(self._shutdown_timeout)
        runner.idle.connect(self._on_idle)
        central = QWidget()
        layout = QHBoxLayout(central)
        self.sidebar = QListWidget()
        self.sidebar.addItems([
            "LIVE", "CALIBRACIÓN", "DETECCIÓN", "ANALÍTICA",
            "REPORTES", "DIAGNÓSTICOS", "AJUSTES",
        ])
        self.sidebar.setMaximumWidth(220)
        self.stack = QStackedWidget()
        self.live = LiveScreen(controller)
        if operations is not None:
            self.live.set_operations(operations)
            operations.service.storage.idle.connect(self._on_idle)
            operations.service.network.idle.connect(self._on_idle)
            if operations.service.discovery is not None:
                operations.service.discovery.idle.connect(self._on_idle)
        if vision is not None:
            self.live.set_vision(vision)
            vision.runner.idle.connect(self._on_idle)
        self.calibration_screen = CalibrationScreen(service=calibration,
                                                    camera=controller if calibration else None, vision=vision)
        if operations is not None:
            self.calibration_screen.unit.setText("mm")
            self.calibration_screen.unit.setReadOnly(True)
        self.detection_screen = DetectionScreen(controller=vision)
        self.calibration_screen.idle.connect(self._on_idle)
        self.analytics_screen = AnalyticsScreen(operations=operations)
        self.reports_screen = ReportsScreen(operations=operations)
        self.diagnostics_screen = DiagnosticsScreen(operations=operations)
        self.settings_screen = SettingsScreen(operations=operations)
        for screen in (
            self.live, self.calibration_screen, self.detection_screen, self.analytics_screen,
            self.reports_screen, self.diagnostics_screen, self.settings_screen,
        ):
            self.stack.addWidget(screen)
        self.sidebar.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.sidebar.setCurrentRow(0)
        layout.addWidget(self.sidebar)
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(central)
        controller.on_state.append(self.update_camera_status)
        self.update_camera_status(controller.runtime)

    def update_camera_status(self, runtime: CameraRuntimeState) -> None:
        if self._closing:
            return
        descriptions = {
            CameraState.DISCONNECTED: "Cámara desconectada",
            CameraState.DISCOVERING: "Buscando cámaras…",
            CameraState.CONNECTING: "Conectando cámara…",
            CameraState.STREAMING: "Cámara conectada · Video en vivo",
            CameraState.RECOVERING: "Recuperando conexión de cámara…",
            CameraState.ERROR: "Error de cámara",
            CameraState.STOPPING: "Deteniendo cámara…",
        }
        message = f"Percepción local · {descriptions[runtime.state]}"
        if runtime.state is CameraState.ERROR and runtime.last_error is not None:
            message += f" · {runtime.last_error.message}"
        if self.statusBar().currentMessage() != message:
            self.statusBar().showMessage(message)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._operations_active():
            event.ignore()
            if not self._closing:
                self._closing = True
                logger.info("application_closing")
                self.centralWidget().setEnabled(False)
                if self.operations is not None:
                    self.operations.shutdown()
                if self.vision is not None:
                    self.vision.stop()
                self.calibration_screen.cancel()
                self.controller.disconnect()
                self._finish_storage_if_safe()
                self.statusBar().showMessage("Cerrando: esperando liberación de cámara y visión…")
                self.shutdown_timer.start()
            return
        self.shutdown_timer.stop()
        if not self._closing:
            logger.info("application_closing")
        self.controller.disconnect()
        self.live.dispose()
        self.detection_screen.dispose()
        self.calibration_screen.dispose()
        self.analytics_screen.dispose()
        self.diagnostics_screen.dispose()
        if self.operations is not None:
            self.operations.dispose()
        if self.vision is not None:
            self.vision.dispose()
        if self.update_camera_status in self.controller.on_state:
            self.controller.on_state.remove(self.update_camera_status)
        logger.info("application_closed")
        event.accept()

    @Slot()
    def _shutdown_timeout(self) -> None:
        if self._operations_active():
            logger.error("camera_shutdown_timeout")
            component = ("el driver de cámara sigue bloqueado" if self.runner.active else
                         "la operación de visión/calibración sigue activa" if self.calibration_screen.busy or self.vision and self.vision.runner.active else
                         "la operación de red/storage/discovery sigue activa")
            self.statusBar().showMessage(f"No se pudo completar el cierre: {component}. "
                                        "La ventana permanecerá abierta hasta que termine la operación.")

    def _operations_active(self) -> bool:
        return (self.runner.active or self.calibration_screen.busy
                or self.vision is not None and self.vision.runner.active
                or self.operations is not None and self.operations.active)

    def _finish_storage_if_safe(self) -> None:
        if (self.operations is not None and not self.runner.active and not self.calibration_screen.busy
                and (self.vision is None or not self.vision.runner.active)):
            self.operations.finish_storage()

    @Slot()
    def _on_idle(self) -> None:
        if self._closing:
            self._finish_storage_if_safe()
            self.close()
