from PySide6.QtWidgets import (
    QCheckBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from ...domain.models.detection import DetectionParameters
from ...domain.models.vision_observation import VisionPipelineState
from ..vision_text import (
    CALIBRATION_TEXT, DETECTION_TEXT, PIPELINE_TEXT, TRACKING_TEXT,
    milliseconds, position_text,
)


class DetectionScreen(QWidget):
    def __init__(self, parent=None, controller=None) -> None:
        super().__init__(parent)
        self.controller = controller
        outer = QVBoxLayout(self)
        heading = QLabel("DETECCIÓN")
        heading.setObjectName("heading")
        outer.addWidget(heading)
        if controller is None:
            outer.addWidget(QLabel("Módulo preparado. La funcionalidad requiere los servicios de SPEC-01."))
            outer.addStretch()
            return
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        self.state_label = QLabel()
        self.result_label = QLabel("Sin observación actual. X/Y/Z físicos: No disponibles.")
        self.result_label.setWordWrap(True)
        self.metrics_label = QLabel()
        self.metrics_label.setWordWrap(True)
        self.message = QLabel("Introduce parámetros explícitos. No hay valores operativos del hardware predefinidos.")
        self.message.setWordWrap(True)
        layout.addWidget(self.state_label)
        layout.addWidget(self.result_label)
        layout.addWidget(self.metrics_label)
        form = QFormLayout()
        self.fields = {}
        labels = {
            "hue_min": "H mínimo (0–179)", "hue_max": "H máximo (0–179)",
            "saturation_min": "S mínimo (0–255)", "saturation_max": "S máximo (0–255)",
            "value_min": "V mínimo (0–255)", "value_max": "V máximo (0–255)",
            "min_area": "Área mínima (píxeles²)", "max_area": "Área máxima (opcional, píxeles²)",
            "minimum_confidence": "Calidad mínima (0–1)",
            "morphology_kernel_size": "Kernel morfológico (impar, si se activa)",
            "alpha": "Alpha EMA (0 < alpha ≤ 1)",
        }
        self.field_labels = labels
        for name, text in labels.items():
            field = QLineEdit()
            field.setPlaceholderText("Opcional" if name == "max_area" else "Introducir valor")
            self.fields[name] = field
            form.addRow(text, field)
        self.morphology = QCheckBox("Activar apertura y cierre morfológicos")
        form.addRow(self.morphology)
        layout.addLayout(form)
        layout.addWidget(QLabel("Calidad = solidez × ocupación celeste. No es probabilidad de detección."))
        buttons = QHBoxLayout()
        self.apply_button = QPushButton("Aplicar parámetros")
        self.start_button = QPushButton("Iniciar detector")
        self.stop_button = QPushButton("Detener detector")
        for button in (self.apply_button, self.start_button, self.stop_button):
            buttons.addWidget(button)
        layout.addLayout(buttons)
        layout.addWidget(self.message)
        layout.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)
        self.apply_button.clicked.connect(self.apply_parameters)
        self.start_button.clicked.connect(self.start)
        self.stop_button.clicked.connect(controller.stop)
        controller.on_state.append(self.update_state)
        controller.on_result.append(self.update_result)
        self.update_state()

    def apply_parameters(self) -> bool:
        try:
            values = {}
            for name in ("hue_min", "hue_max", "saturation_min", "saturation_max", "value_min", "value_max"):
                values[name] = self._number(name, int)
            values["min_area"] = self._number("min_area", float)
            text = self.fields["max_area"].text().strip()
            values["max_area"] = self._number("max_area", float) if text else None
            values["minimum_confidence"] = self._number("minimum_confidence", float)
            values["morphology_enabled"] = self.morphology.isChecked()
            kernel = self.fields["morphology_kernel_size"].text().strip()
            values["morphology_kernel_size"] = self._number("morphology_kernel_size", int) if kernel else None
            alpha = self._number("alpha", float)
            self.controller.configure(DetectionParameters(**values), alpha)
            self.message.setText("Parámetros aplicados. Validar físicamente con el gancho y la iluminación reales.")
            return True
        except ValueError as exc:
            self.message.setText(f"Configuración inválida: {exc}")
            return False

    def _number(self, name: str, cast):
        try:
            return cast(self.fields[name].text().strip())
        except ValueError as exc:
            raise ValueError(f"Introduce un número válido en «{self.field_labels[name]}».") from exc

    def start(self) -> None:
        if not self.apply_parameters():
            return
        try:
            self.controller.start()
        except ValueError as exc:
            self.message.setText(str(exc))

    def update_state(self) -> None:
        controller = self.controller
        self.state_label.setText(
            f"Visión: {PIPELINE_TEXT[controller.state]} · "
            f"Calibración: {CALIBRATION_TEXT[controller.calibration.status]}"
        )
        self.start_button.setEnabled(not controller.runner.active)
        self.stop_button.setEnabled(controller.runner.active or controller.state is VisionPipelineState.ERROR)
        if controller.last_result is None:
            self.result_label.setText("Sin observación actual. X/Y/Z físicos: No disponibles.")
            self.metrics_label.clear()
        if controller.last_error:
            self.message.setText(controller.last_error)

    def update_result(self, result) -> None:
        observation, metrics = result.observation, result.metrics
        detection, tracking = observation.detection, observation.tracking
        geometry = ""
        if detection.bounding_box is not None:
            box = detection.bounding_box
            geometry = (f"\nCaja: ({box.x:.1f}, {box.y:.1f}, {box.width:.1f}, {box.height:.1f}) · "
                        f"Centroide: ({detection.centroid.u:.1f}, {detection.centroid.v:.1f}) px")
        self.result_label.setText(
            f"{DETECTION_TEXT[observation.detection_state]} · Tracking: {TRACKING_TEXT[tracking.state]} · "
            f"Calidad actual: {detection.confidence:.3f}{geometry}\n"
            f"{position_text(observation.position)}\nFrame {observation.frame_sequence} · "
            f"{observation.timestamp.astimezone().isoformat(timespec='milliseconds')}"
        )
        self.metrics_label.setText(
            f"FPS pipeline: {metrics.pipeline_fps:.1f} · Preprocess: {milliseconds(metrics.preprocess_ms)} · "
            f"Detección: {milliseconds(metrics.detection_ms)} · Tracking: {milliseconds(metrics.tracking_ms)} · "
            f"Posición: {milliseconds(metrics.position_ms)} · EMA: {milliseconds(metrics.filter_ms)} · "
            f"Total: {metrics.total_ms:.2f} ms\nProcesados: {metrics.frames_processed} · "
            f"Intermedios omitidos: {metrics.skipped_frames} · Pérdidas: {metrics.lost_tracking} · "
            f"Reacquisiciones: {metrics.reacquisitions}"
        )

    def dispose(self) -> None:
        if self.controller is not None:
            for callbacks, callback in ((self.controller.on_state, self.update_state),
                                        (self.controller.on_result, self.update_result)):
                if callback in callbacks:
                    callbacks.remove(callback)
