from threading import Event

import pyqtgraph as pg
from PySide6.QtCore import QThread, QTimer, Qt, Signal, Slot
from PySide6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from ...domain.models.calibration import CalibrationPoint
from ...domain.models.camera_state import CameraState
from ...domain.models.frame import Frame
from ...domain.models.geometry import ImagePoint, PhysicalPoint2D
from ..vision_text import CALIBRATION_TEXT
from ..widgets.video_widget import VideoWidget
from ..widgets.accuracy_widget import AccuracyWidget


class CalibrationWorker(QThread):
    result = Signal(object)
    error = Signal(str)

    def __init__(self, service, points, geometry, cancellation, parent=None) -> None:
        super().__init__(parent)
        self.service, self.points, self.geometry = service, points, geometry
        self.cancellation = cancellation

    def run(self) -> None:
        try:
            candidate = self.service.compute(self.points, *self.geometry)
            if not self.cancellation.is_set():
                self.result.emit(candidate)
        except Exception as exc:
            if not self.cancellation.is_set():
                self.error.emit(str(exc))


class CalibrationScreen(QWidget):
    idle = Signal()

    def __init__(self, parent=None, service=None, camera=None, vision=None) -> None:
        super().__init__(parent)
        self.service, self.camera = service, camera
        self.reference: Frame | None = None
        self.reference_camera_id: str | None = None
        self.candidate = None
        self._worker: CalibrationWorker | None = None
        self._cancellation = Event()
        layout = QVBoxLayout(self)
        heading = QLabel("CALIBRACIÓN")
        heading.setObjectName("heading")
        layout.addWidget(heading)
        if service is None or camera is None:
            layout.addWidget(QLabel("Módulo preparado. La funcionalidad requiere los servicios de SPEC-01."))
            layout.addStretch()
            return
        self.state_label = QLabel()
        self.message = QLabel("Obtén un frame de referencia y marca cuatro puntos físicos conocidos.")
        self.message.setWordWrap(True)
        self.video = VideoWidget()
        self.markers = pg.ScatterPlotItem(size=10, brush="#ffcf66")
        self.video.view.addItem(self.markers)
        self.point_labels = [pg.TextItem(f"P{i + 1}", color="#ffcf66", anchor=(0, 1)) for i in range(4)]
        for label in self.point_labels:
            self.video.view.addItem(label)
            label.hide()
        layout.addWidget(self.state_label)
        layout.addWidget(self.video, 1)
        self.table = QTableWidget(4, 5)
        self.table.setHorizontalHeaderLabels(["Punto", "u (px)", "v (px)", "X físico", "Y físico"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setMaximumHeight(180)
        for row in range(4):
            for column in range(5):
                item = QTableWidgetItem(f"P{row + 1}" if column == 0 else "")
                if column <= 2:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, column, item)
        self.table.selectRow(0)
        layout.addWidget(self.table)
        self.unit = QLineEdit()
        self.unit.setPlaceholderText("Unidad física declarada para los cuatro puntos (por ejemplo, mm)")
        layout.addWidget(self.unit)
        controls = QHBoxLayout()
        self.reference_button = QPushButton("Obtener frame de referencia")
        self.calculate_button = QPushButton("Calcular")
        self.validate_button = QPushButton("Validar")
        self.apply_button = QPushButton("Aplicar")
        self.invalidate_button = QPushButton("Invalidar")
        self.recalibrate_button = QPushButton("Recalibrar")
        for button in (self.reference_button, self.calculate_button, self.validate_button,
                       self.apply_button, self.invalidate_button, self.recalibrate_button):
            controls.addWidget(button)
        layout.addLayout(controls)
        layout.addWidget(self.message)
        note = QLabel("X horizontal · Y vertical · Z profundidad no disponible. "
                      "El error interno de cuatro puntos NO acredita precisión física: validar con otros puntos.")
        note.setWordWrap(True)
        layout.addWidget(note)
        self.accuracy = AccuracyWidget(vision) if vision is not None else None
        if self.accuracy is not None:
            layout.addWidget(self.accuracy)
        self.video.scene().sigMouseClicked.connect(self._point_clicked)
        self.table.cellChanged.connect(self._points_changed)
        self.unit.textChanged.connect(self._points_changed)
        self.reference_button.clicked.connect(self.take_reference)
        self.recalibrate_button.clicked.connect(self.take_reference)
        self.calculate_button.clicked.connect(self.calculate)
        self.validate_button.clicked.connect(self.validate_candidate)
        self.apply_button.clicked.connect(self.apply_candidate)
        self.invalidate_button.clicked.connect(self.invalidate)
        service.on_change.append(self.update_state)
        camera.on_state.append(self.camera_changed)
        self.update_state()

    @property
    def busy(self) -> bool:
        return self._worker is not None

    def _points_changed(self, *args) -> None:
        self.candidate = None
        self._draw_points()
        self.update_state()

    def _draw_points(self) -> None:
        points = []
        for row, label in enumerate(self.point_labels):
            try:
                u, v = (float(self.table.item(row, column).text()) for column in (1, 2))
                points.append((u, v))
                label.setPos(u, v)
                label.show()
            except ValueError:
                label.hide()
        self.markers.setData([p[0] for p in points], [p[1] for p in points])

    def take_reference(self) -> None:
        if self.busy:
            return
        frame = self.camera.store.latest()
        device = self.camera.runtime.selected_device
        if self.camera.runtime.state is not CameraState.STREAMING or frame is None or device is None:
            self.message.setText("Conecta la cámara antes de obtener un frame de referencia.")
            return
        self.service.begin()
        self.reference = Frame(frame.sequence, frame.captured_at, frame.width, frame.height, frame.image.copy())
        self.reference_camera_id = device.id
        self.candidate = None
        self.table.blockSignals(True)
        for row in range(4):
            for column in range(1, 5):
                self.table.item(row, column).setText("")
        self.table.blockSignals(False)
        self.table.selectRow(0)
        self._draw_points()
        self.video.render(self.reference)
        self.message.setText("Selecciona P1–P4 en la tabla y haz clic en su punto de imagen. Introduce X/Y conocidos y unidad.")
        self.update_state()

    def _point_clicked(self, event) -> None:
        if self.reference is None or self.busy or event.button() != Qt.MouseButton.LeftButton:
            return
        point = self.video.image_item.mapFromScene(event.scenePos())
        u, v = point.x(), point.y()
        if not 0 <= u < self.reference.width or not 0 <= v < self.reference.height:
            return
        row = max(0, self.table.currentRow())
        self.set_image_point(row, ImagePoint(u, v))
        self.table.selectRow(min(3, row + 1))

    def set_image_point(self, row: int, point: ImagePoint) -> None:
        self.table.blockSignals(True)
        self.table.item(row, 1).setText(f"{point.u:.8f}")
        self.table.item(row, 2).setText(f"{point.v:.8f}")
        self.table.blockSignals(False)
        self._points_changed()

    def calculate(self) -> None:
        if self.reference is None or self.busy:
            return
        try:
            points = []
            for row in range(4):
                try:
                    u, v, x, y = (float(self.table.item(row, column).text()) for column in range(1, 5))
                except ValueError as exc:
                    raise ValueError(f"Completa P{row + 1} con valores numéricos para u, v, X e Y.") from exc
                points.append(CalibrationPoint(ImagePoint(u, v), PhysicalPoint2D(x, y, self.unit.text().strip())))
            points = tuple(points)
            self.service.begin()
            self.candidate = None
            self._cancellation = Event()
            geometry = (self.reference_camera_id, self.reference.width, self.reference.height)
            worker = CalibrationWorker(self.service, points, geometry, self._cancellation, self)
            self._worker = worker
            worker.result.connect(self._calculated)
            worker.error.connect(self._failed)
            worker.finished.connect(self._finished)
            self.message.setText("Calculando homografía fuera del hilo de interfaz…")
            self.update_state()
            worker.start()
        except ValueError as exc:
            self.message.setText(f"Correspondencias inválidas: {exc}")

    @Slot(object)
    def _calculated(self, candidate) -> None:
        if not self._cancellation.is_set():
            self.candidate = candidate
            self.message.setText(
                f"Homografía calculada. Error interno: {candidate.internal_reprojection_error:.6g} "
                f"{candidate.unit}. No equivale a precisión física. Validar y aplicar."
            )

    @Slot(str)
    def _failed(self, message: str) -> None:
        if not self._cancellation.is_set():
            self.service.fail(message)
            self.message.setText(message)

    @Slot()
    def _finished(self) -> None:
        worker = self._worker
        if worker is None:
            return
        if not worker.wait(0):
            QTimer.singleShot(0, self._finished)
            return
        self._worker = None
        worker.deleteLater()
        self.update_state()
        self.idle.emit()

    def validate_candidate(self) -> bool:
        candidate = self.candidate
        valid = candidate is not None and self.service.geometry == (
            candidate.camera_id, candidate.width, candidate.height,
        ) and self.camera.runtime.state is CameraState.STREAMING
        self.message.setText("Candidata válida para esta cámara/resolución; precisión física aún no medida."
                             if valid else "No hay candidata válida para la cámara y resolución actuales.")
        return valid

    def apply_candidate(self) -> None:
        if not self.validate_candidate():
            return
        try:
            self.service.apply(self.candidate)
            self.message.setText("Calibración aplicada en memoria. Valida puntos físicos independientes.")
        except ValueError as exc:
            self.message.setText(str(exc))

    def invalidate(self) -> None:
        self.cancel()
        self.candidate = None
        self.reference = None
        self.video.clear_frame()
        self.markers.setData([], [])
        for label in self.point_labels:
            label.hide()
        self.service.invalidate()
        self.message.setText("Calibración invalidada. Recalibra si la cámara o referencias se movieron físicamente.")

    def camera_changed(self, runtime) -> None:
        if self.reference is not None:
            device = runtime.selected_device
            frame = self.camera.store.latest() if runtime.state is CameraState.STREAMING else None
            changed = device is not None and device.id != self.reference_camera_id
            changed |= frame is not None and (frame.width, frame.height) != (self.reference.width, self.reference.height)
            if changed:
                self.cancel()
                self.reference = None
                self.candidate = None
                self.video.clear_frame()
                self.markers.setData([], [])
                for label in self.point_labels:
                    label.hide()
                self.message.setText("Cámara o resolución cambiadas. Obtén un nuevo frame de referencia.")
        self.update_state()

    def update_state(self) -> None:
        if self.service is None:
            return
        geometry = self.service.geometry
        self.state_label.setText(
            f"Estado: {CALIBRATION_TEXT[self.service.status]} · "
            f"Cámara/resolución: {geometry if geometry else 'No disponible'}"
        )
        streaming = self.camera.runtime.state is CameraState.STREAMING
        self.reference_button.setEnabled(streaming and not self.busy)
        self.recalibrate_button.setEnabled(streaming and not self.busy)
        self.calculate_button.setEnabled(streaming and self.reference is not None and not self.busy)
        self.validate_button.setEnabled(self.candidate is not None and not self.busy)
        self.apply_button.setEnabled(streaming and self.candidate is not None and not self.busy)
        self.table.setEnabled(not self.busy)
        self.unit.setEnabled(not self.busy)

    def cancel(self) -> None:
        self._cancellation.set()

    def dispose(self) -> None:
        self.cancel()
        if getattr(self, "accuracy", None) is not None:
            self.accuracy.dispose()
        if self.service is not None:
            if self.update_state in self.service.on_change:
                self.service.on_change.remove(self.update_state)
            if self.camera_changed in self.camera.on_state:
                self.camera.on_state.remove(self.camera_changed)
