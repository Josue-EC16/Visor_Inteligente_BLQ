from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from ...application.accuracy_metrics import AccuracyAccumulator
from ...domain.models.geometry import PhysicalPoint2D
from ...domain.models.vision_observation import VisionPipelineState


class AccuracyWidget(QWidget):
    def __init__(self, vision, parent=None) -> None:
        super().__init__(parent)
        self.vision = vision
        self.raw = AccuracyAccumulator()
        self.filtered = AccuracyAccumulator()
        layout = QVBoxLayout(self)
        label = QLabel("Validación independiente: coloca el gancho en un punto conocido que no se usó para calibrar.")
        label.setWordWrap(True)
        layout.addWidget(label)
        controls = QHBoxLayout()
        self.x = QLineEdit()
        self.x.setPlaceholderText("X real, unidad de calibración")
        self.y = QLineEdit()
        self.y.setPlaceholderText("Y real, unidad de calibración")
        self.measure_button = QPushButton("Medir error actual")
        self.reset_button = QPushButton("Reiniciar mediciones")
        for widget in (self.x, self.y, self.measure_button, self.reset_button):
            controls.addWidget(widget)
        layout.addLayout(controls)
        self.summary = QLabel("Sin mediciones independientes. No hay umbral físico aprobado.")
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        self.measure_button.clicked.connect(self.measure)
        self.reset_button.clicked.connect(self.reset)
        vision.on_state.append(self.update_state)
        vision.on_result.append(self.result_changed)
        vision.calibration.on_change.append(self.reset)
        self.update_state()

    def update_state(self) -> None:
        result = self.vision.last_result
        self.measure_button.setEnabled(self.vision.state is VisionPipelineState.RUNNING
                                       and result is not None and result.observation.position is not None)

    def result_changed(self, result) -> None:
        self.update_state()

    def reset(self) -> None:
        self.raw = AccuracyAccumulator()
        self.filtered = AccuracyAccumulator()
        self.summary.setText("Sin mediciones independientes. No hay umbral físico aprobado.")

    def measure(self) -> None:
        try:
            result = self.vision.last_result
            if self.vision.state is not VisionPipelineState.RUNNING or result is None or result.observation.position is None:
                raise ValueError("No existe una posición actual calibrada para medir.")
            estimate = result.observation.position
            try:
                x, y = float(self.x.text()), float(self.y.text())
            except ValueError as exc:
                raise ValueError("Introduce X real e Y real como números válidos.") from exc
            reference = PhysicalPoint2D(x, y, estimate.raw_position.unit)
            raw = self.raw.add(estimate.raw_position, reference)
            filtered = self.filtered.add(estimate.filtered_position, reference)
            self.summary.setText(
                f"N={raw.count}, unidad={reference.unit}, frame={result.frame.sequence}\n"
                f"Raw: MAE X={raw.mae_x:.4g}, MAE Y={raw.mae_y:.4g}, "
                f"error 2D medio={raw.mean_2d_error:.4g}, máximo={raw.maximum_2d_error:.4g}\n"
                f"Filtrada: MAE X={filtered.mae_x:.4g}, MAE Y={filtered.mae_y:.4g}, "
                f"error 2D medio={filtered.mean_2d_error:.4g}, máximo={filtered.maximum_2d_error:.4g}\n"
                "Resultados en memoria: registrar para la validación física. No autorizan movimiento."
            )
        except (ValueError, TypeError) as exc:
            self.summary.setText(str(exc))

    def dispose(self) -> None:
        for callbacks, callback in (
            (self.vision.on_state, self.update_state), (self.vision.on_result, self.result_changed),
            (self.vision.calibration.on_change, self.reset),
        ):
            if callback in callbacks:
                callbacks.remove(callback)
