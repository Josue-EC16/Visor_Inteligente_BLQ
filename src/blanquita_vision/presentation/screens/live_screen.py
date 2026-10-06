import logging

from PySide6.QtWidgets import (
    QComboBox, QGridLayout, QHBoxLayout, QLabel, QPushButton,
    QVBoxLayout, QWidget,
)

from ...application.camera_controller import CameraController
from ...domain.models.camera_device import CameraDevice
from ...domain.models.camera_state import CameraError, CameraRuntimeState, CameraState
from ...domain.models.frame import CapturedFrame, Frame
from ...domain.models.vision_observation import VisionPipelineState
from ..vision_text import CALIBRATION_TEXT, DETECTION_TEXT, PIPELINE_TEXT, TRACKING_TEXT, position_text
from ..widgets.video_widget import VideoWidget

logger = logging.getLogger(__name__)

STATE_TEXT = {
    CameraState.DISCONNECTED: "Desconectada",
    CameraState.DISCOVERING: "Buscando cámaras…",
    CameraState.CONNECTING: "Conectando…",
    CameraState.STREAMING: "Transmitiendo",
    CameraState.RECOVERING: "Recuperando conexión…",
    CameraState.ERROR: "Error",
    CameraState.STOPPING: "Deteniendo…",
}
STATE_COLOR = {
    CameraState.DISCONNECTED: "#bfc4cc",
    CameraState.DISCOVERING: "#ffcf66",
    CameraState.CONNECTING: "#ffcf66",
    CameraState.STREAMING: "#79e2a4",
    CameraState.RECOVERING: "#ffcf66",
    CameraState.ERROR: "#ff8585",
    CameraState.STOPPING: "#ffcf66",
}


class LiveScreen(QWidget):
    def __init__(self, controller: CameraController, parent=None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.vision = None
        self.operations = None
        self.last_processed_sequence: int | None = None
        # Una sola captura retenida: el feedback no acumula imágenes en memoria.
        self.last_capture: CapturedFrame | None = None
        layout = QVBoxLayout(self)
        heading = QLabel("LIVE")
        heading.setObjectName("heading")
        layout.addWidget(heading)
        self.video = VideoWidget()
        layout.addWidget(self.video, 1)
        self.message = QLabel("No se detectaron cámaras disponibles. Pulsa Actualizar cámaras.")
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        grid = QGridLayout()
        self.state_label = QLabel()
        self.device_label = QLabel()
        self.resolution_label = QLabel()
        self.fps_label = QLabel()
        self.backend_label = QLabel()
        self.metrics_label = QLabel()
        self.metrics_label.setWordWrap(True)
        grid.addWidget(self.state_label, 0, 0)
        grid.addWidget(self.device_label, 0, 1)
        grid.addWidget(self.resolution_label, 1, 0)
        grid.addWidget(self.fps_label, 1, 1)
        grid.addWidget(self.backend_label, 2, 0)
        grid.addWidget(self.metrics_label, 2, 1)
        layout.addLayout(grid)
        self.selector = QComboBox()
        self.selector.addItem("Selecciona una cámara", None)
        self.selector.currentIndexChanged.connect(self._select)
        layout.addWidget(self.selector)
        controls = QHBoxLayout()
        self.refresh_button = QPushButton("Actualizar cámaras")
        self.connect_button = QPushButton("Conectar")
        self.disconnect_button = QPushButton("Desconectar")
        self.capture_button = QPushButton("Capturar frame")
        self.retry_button = QPushButton("Reintentar")
        for button in (self.refresh_button, self.connect_button,
                       self.disconnect_button, self.capture_button, self.retry_button):
            controls.addWidget(button)
        layout.addLayout(controls)
        self.refresh_button.clicked.connect(controller.refresh)
        self.connect_button.clicked.connect(controller.connect)
        self.disconnect_button.clicked.connect(controller.disconnect)
        self.capture_button.clicked.connect(self._capture)
        self.retry_button.clicked.connect(controller.connect)
        controller.on_state.append(self.update_state)
        controller.on_frame.append(self.render)
        controller.on_devices.append(self.update_devices)
        self.update_state(controller.runtime)

    def dispose(self) -> None:
        for callbacks, callback in (
            (self.controller.on_state, self.update_state),
            (self.controller.on_frame, self.render),
            (self.controller.on_devices, self.update_devices),
        ):
            if callback in callbacks:
                callbacks.remove(callback)
        self.last_capture = None
        self.video.clear_frame()
        if self.vision is not None:
            for callbacks, callback in ((self.vision.on_state, self.update_vision_state),
                                        (self.vision.on_result, self.render_observation)):
                if callback in callbacks:
                    callbacks.remove(callback)

    def set_vision(self, vision) -> None:
        self.vision = vision
        self.vision_label = QLabel()
        self.vision_label.setWordWrap(True)
        self.layout().insertWidget(3, self.vision_label)
        vision.on_state.append(self.update_vision_state)
        vision.on_result.append(self.render_observation)
        self.update_vision_state()

    def set_operations(self, operations) -> None:
        self.operations = operations
        self.network_label = QLabel()
        self.network_label.setWordWrap(True)
        self.layout().insertWidget(3, self.network_label)
        operations.changed.connect(self.update_network)
        self.update_network()

    def update_network(self) -> None:
        health = self.operations.service.network.server.health()
        states = {"STOPPED": "Detenido", "STARTING": "Iniciando", "LISTENING": "Escuchando",
                  "CLIENT_CONNECTED": "Cliente conectado", "STOPPING": "Deteniendo", "ERROR": "Error"}
        self.network_label.setText(
            f"Vision Server: {states.get(health['state'], health['state'])} · "
            f"Mobile: {'Conectado' if health['client'] else 'Desconectado'} · "
            f"Último TX (UTC): {health['last_tx'] or 'No disponible'}"
        )

    def update_vision_state(self) -> None:
        if self.vision.last_result is None:
            self.last_processed_sequence = None
            self.video.clear_overlay()
            self.vision_label.setText(
                f"Visión: {PIPELINE_TEXT[self.vision.state]} · "
                f"Calibración: {CALIBRATION_TEXT[self.vision.calibration.status]} · "
                "X/Y/Z físicos: No disponibles"
            )
            if self.vision.last_error:
                self.vision_label.setText(self.vision_label.text() + f" · {self.vision.last_error}")
            if self.vision.state in (VisionPipelineState.STOPPED, VisionPipelineState.ERROR):
                frame = self.controller.store.latest()
                if frame is not None and self.controller.runtime.state is CameraState.STREAMING:
                    self.render(frame)
            else:
                self.video.clear_frame()

    def render_observation(self, result) -> None:
        observation = result.observation
        try:
            self.video.render(result.frame)
            tracking = observation.tracking
            detection = observation.detection
            self.video.set_overlay(tracking.bounding_box, tracking.centroid,
                                   f"gancho · Calidad {detection.confidence:.3f}")
            self.last_processed_sequence = result.frame.sequence
            self.vision_label.setText(
                f"{DETECTION_TEXT[observation.detection_state]} · "
                f"Tracking: {TRACKING_TEXT[tracking.state]} · "
                f"Calibración: {CALIBRATION_TEXT[observation.calibration_status]}\n"
                f"{position_text(observation.position)} · Calidad: {detection.confidence:.3f} · "
                f"Pipeline: {result.metrics.pipeline_fps:.1f} FPS / {result.metrics.total_ms:.2f} ms"
            )
            self.message.setText(
                f"Frame procesado {result.frame.sequence} · "
                f"{observation.timestamp.astimezone().isoformat(timespec='milliseconds')}"
            )
        except Exception:
            logger.error("vision_render_failed", exc_info=True)
            self.video.clear_overlay()
            self.vision_label.setText("Error al visualizar la observación de visión.")

    def _select(self) -> None:
        device_id = self.selector.currentData()
        self.controller.select(device_id)

    def update_devices(self, devices: list[CameraDevice]) -> None:
        selected = self.controller.runtime.selected_device
        self.selector.blockSignals(True)
        self.selector.clear()
        self.selector.addItem("Selecciona una cámara", None)
        for device in devices:
            self.selector.addItem(device.display_name, device.id)
        if selected is not None:
            self.selector.setCurrentIndex(self.selector.findData(selected.id))
        self.selector.blockSignals(False)
        self.update_state(self.controller.runtime)

    def update_state(self, runtime: CameraRuntimeState) -> None:
        state = runtime.state
        active = self.controller.runner.active
        self.state_label.setText(f"Estado: {STATE_TEXT[state]}")
        self.state_label.setStyleSheet(f"color: {STATE_COLOR[state]}; font-weight: bold;")
        selected = runtime.selected_device
        self.device_label.setText(f"Cámara: {selected.display_name if selected else 'Sin selección'}")
        properties = runtime.properties
        resolution = "No disponible"
        fps = "No disponible"
        backend = "No disponible"
        if properties is not None:
            if properties.width and properties.height:
                resolution = f"{properties.width} × {properties.height}"
            if properties.reported_fps is not None:
                fps = f"{properties.reported_fps:.1f}"
            backend = properties.backend_name or backend
        self.resolution_label.setText(f"Resolución: {resolution}")
        self.fps_label.setText(f"FPS reportado: {fps}")
        self.backend_label.setText(f"Backend: {self.controller.backend} / efectivo: {backend}")
        metrics = self.controller.store.metrics()
        measured = f"{metrics.measured_fps:.1f}" if metrics.measured_fps is not None else "No disponible"
        self.metrics_label.setText(
            f"FPS medido: {measured} · Frames: {metrics.frames_captured} · "
            f"Inválidos: {metrics.invalid_frames} · Reemplazados: {metrics.stale_frames_replaced} · "
            f"Reintentos: {metrics.reconnect_attempts}"
        )
        idle = not active and state in (CameraState.DISCONNECTED, CameraState.ERROR)
        self.selector.setEnabled(idle)
        self.refresh_button.setEnabled(idle)
        self.connect_button.setEnabled(idle and selected is not None)
        self.disconnect_button.setEnabled(active and state is not CameraState.STOPPING)
        self.capture_button.setEnabled(
            state is CameraState.STREAMING and self.controller.store.latest() is not None
        )
        self.retry_button.setVisible(state is CameraState.ERROR)
        self.retry_button.setEnabled(idle and selected is not None)
        if state is not CameraState.STREAMING:
            self.video.clear_frame()
            self.last_capture = None
            if runtime.last_error:
                self.message.setText(runtime.last_error.message)
            elif state is CameraState.DISCONNECTED:
                self.message.setText(
                    "Selecciona una cámara y pulsa Conectar." if self.controller.devices
                    else "No se detectaron cámaras disponibles. Pulsa Actualizar cámaras."
                )
            else:
                self.message.setText(STATE_TEXT[state])
        elif runtime.last_frame_at is None:
            self.message.setText("Esperando video actual…")

    def render(self, frame: Frame) -> None:
        if self.vision is not None and self.vision.state in (
            VisionPipelineState.STARTING, VisionPipelineState.RUNNING, VisionPipelineState.STOPPING,
        ):
            return
        try:
            self.video.clear_overlay()
            self.video.render(frame)
            self.message.setText(f"Último frame: {frame.captured_at.astimezone().isoformat(timespec='milliseconds')}")
        except Exception:
            logger.error("frame_render_failed", exc_info=True)
            self.video.clear_frame()
            self.message.setText("Error al visualizar el frame. La captura continúa.")

    def _capture(self) -> None:
        if self.operations is not None:
            self.message.setText("Guardando captura manual fuera del hilo de UI…")
            self.operations.service.capture(lambda result, error: self.message.setText(
                f"No se completó la captura: {error}" if error else f"Captura guardada: {result['relative_path']}"))
            return
        try:
            self.last_capture = self.controller.capture()
            self.message.setText(
                f"Frame {self.last_capture.source_sequence} capturado en memoria."
            )
        except CameraError as exc:
            self.message.setText(exc.message)
        except Exception:
            logger.error("snapshot_failed", exc_info=True)
            self.message.setText("No se pudo obtener la copia del frame.")
