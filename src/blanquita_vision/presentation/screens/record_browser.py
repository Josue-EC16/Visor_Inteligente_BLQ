import json
from datetime import datetime

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from ...domain.models.protocol import utc_text

CATEGORIES = {
    "Sesiones": "vision_sessions", "Detecciones": "detections", "VisionReports": "vision_reports",
    "Capturas": "captures", "Calibraciones": "calibrations", "Eventos": "events", "Errores": "errors",
}

COLUMN_LABELS = {
    "session_id": "Sesión", "started_at_utc": "Inicio (hora local)", "ended_at_utc": "Fin (hora local)",
    "start_source": "Origen", "end_reason": "Motivo de cierre", "camera_id": "Cámara",
    "width": "Ancho", "height": "Alto", "frame_sequence": "Frame", "timestamp_utc": "Fecha (hora local)",
    "message_id": "ID de mensaje", "detection_id": "ID de detección", "detected": "Detectado",
    "object_name": "Objeto", "confidence": "Calidad", "calibration_id": "Calibración", "unit": "Unidad",
    "created_at_utc": "Creación (hora local)", "invalidated_at_utc": "Invalidación (hora local)",
    "status": "Estado", "calibration_status": "Estado calibración", "tracking_state": "Estado tracking",
    "tracking_source": "Fuente tracking", "relative_path": "Ruta", "capture_id": "Captura", "format": "Formato",
    "event_id": "Evento", "event_type": "Tipo de evento", "category": "Categoría", "severity": "Nivel",
    "error_id": "Error", "component": "Componente", "code": "Código", "message": "Mensaje", "recoverable": "Recuperable",
    "x_mm": "X (mm)", "y_mm": "Y (mm)", "z_mm": "Z (mm)", "angle": "Ángulo",
    "raw_x_mm": "X raw (mm)", "raw_y_mm": "Y raw (mm)", "filtered_x_mm": "X filtrada (mm)", "filtered_y_mm": "Y filtrada (mm)",
    "observation_timestamp_utc": "Observación (hora local)", "envelope_timestamp_utc": "Mensaje (hora local)",
    "bbox_x": "Caja X", "bbox_y": "Caja Y", "bbox_w": "Caja ancho", "bbox_h": "Caja alto",
    "centroid_u": "Centroide u", "centroid_v": "Centroide v", "metadata_json": "Metadata JSON",
    "details_json": "Detalle JSON", "homography_json": "Homografía JSON", "payload_json": "Mensaje JSON",
    "window_start_utc": "Ventana inicio (hora local)", "window_end_utc": "Ventana fin (hora local)",
    "metric_id": "Muestra", "capture_fps_avg": "FPS captura", "pipeline_fps_avg": "FPS pipeline",
    "preprocess_ms_avg": "Preprocess (ms)", "detection_ms_avg": "Detección (ms)", "tracking_ms_avg": "Tracking (ms)",
    "position_ms_avg": "Posición (ms)", "filter_ms_avg": "EMA (ms)", "total_ms_avg": "Total (ms)",
    "confidence_avg": "Calidad", "detections_count": "Detecciones", "tracking_lost_count": "Pérdidas tracking",
    "reacquisitions_count": "Reacquisiciones", "errors_count": "Errores", "raw_x_avg_mm": "X raw (mm)",
    "raw_y_avg_mm": "Y raw (mm)", "filtered_x_avg_mm": "X filtrada (mm)", "filtered_y_avg_mm": "Y filtrada (mm)",
}


class RecordBrowser(QWidget):
    def __init__(self, operations, categories=None, parent=None) -> None:
        super().__init__(parent)
        self.operations = operations
        self.rows = []
        self.offset = 0
        self._request = 0
        self.on_rows = []
        layout = QVBoxLayout(self)
        filters = QHBoxLayout()
        self.category = QComboBox()
        for label, table in (categories or CATEGORIES).items():
            self.category.addItem(label, table)
        self.session = QLineEdit()
        self.session.setPlaceholderText("ID de sesión (opcional)")
        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar")
        self.start = QLineEdit()
        self.start.setPlaceholderText("Desde: ISO con zona, opcional")
        self.end = QLineEdit()
        self.end.setPlaceholderText("Hasta: ISO con zona, opcional")
        self.refresh_button = QPushButton("Consultar")
        for widget in (self.category, self.session, self.search, self.start, self.end, self.refresh_button):
            filters.addWidget(widget)
        layout.addLayout(filters)
        self.table = QTableWidget()
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self.show_detail)
        layout.addWidget(self.table, 1)
        self.detail = QPlainTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setMaximumHeight(140)
        self.detail.setPlaceholderText("Detalle estructurado: timestamps originales UTC y unidad mm.")
        layout.addWidget(self.detail)
        buttons = QHBoxLayout()
        self.previous_button = QPushButton("Anterior")
        self.next_button = QPushButton("Siguiente")
        self.json_button = QPushButton("Exportar JSON")
        self.csv_button = QPushButton("Exportar CSV")
        self.open_button = QPushButton("Abrir captura")
        for button in (self.previous_button, self.next_button, self.json_button, self.csv_button, self.open_button):
            buttons.addWidget(button)
        layout.addLayout(buttons)
        self.message = QLabel("Selecciona filtros y consulta. La tabla muestra fechas en hora local.")
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        self.refresh_button.clicked.connect(lambda: self.load(0))
        self.previous_button.clicked.connect(lambda: self.load(max(0, self.offset - 50)))
        self.next_button.clicked.connect(lambda: self.load(self.offset + 50))
        self.category.currentIndexChanged.connect(lambda: self.load(0))
        self.json_button.clicked.connect(lambda: self.choose_export("json"))
        self.csv_button.clicked.connect(lambda: self.choose_export("csv"))
        self.open_button.clicked.connect(self.open_capture)

    def filters(self) -> dict:
        filters = dict(session_id=self.session.text().strip(), search=self.search.text().strip())
        for key, field in (("start", self.start), ("end", self.end)):
            if field.text().strip():
                try:
                    filters[key] = utc_text(datetime.fromisoformat(field.text().strip()))
                except ValueError as exc:
                    raise ValueError("Los filtros temporales requieren ISO-8601 con zona horaria.") from exc
        if filters.get("start") and filters.get("end") and filters["start"] > filters["end"]:
            raise ValueError("El inicio del rango no puede ser posterior al final.")
        return filters

    def load(self, offset=0) -> None:
        try:
            filters = self.filters()
        except ValueError as exc:
            self.message.setText(str(exc))
            return
        self.offset = offset
        self._request += 1
        request = self._request
        self.message.setText("Consultando fuera del hilo UI…")
        self.rows = []
        self.table.setRowCount(0)
        self.detail.clear()
        def received(rows, error):
            if request != self._request:
                return
            if error:
                self.message.setText(f"Error de consulta: {error}")
                return
            self.rows = rows
            columns = list(rows[0]) if rows else []
            self.table.clear()
            self.table.setColumnCount(len(columns))
            self.table.setHorizontalHeaderLabels([COLUMN_LABELS.get(column, column) for column in columns])
            self.table.setRowCount(len(rows))
            for index, record in enumerate(rows):
                for column, key in enumerate(columns):
                    value = record[key]
                    if key.endswith("_utc") and value is not None:
                        value = datetime.fromisoformat(value).astimezone().isoformat(timespec="milliseconds")
                    self.table.setItem(index, column, QTableWidgetItem("No disponible" if value is None else str(value)))
            self.detail.clear()
            self.previous_button.setEnabled(self.offset > 0)
            self.next_button.setEnabled(len(rows) == 50)
            self.open_button.setEnabled(self.category.currentData() == "captures" and bool(rows))
            self.message.setText(f"Página {self.offset // 50 + 1}: {len(rows)} filas." if rows else "Sin datos para los filtros seleccionados.")
            for callback in tuple(self.on_rows):
                callback(rows)
        self.operations.service.storage.submit("query", dict(category=self.category.currentData(), filters=filters,
                                                            limit=50, offset=offset), callback=received)

    def show_detail(self) -> None:
        row = self.table.currentRow()
        if 0 <= row < len(self.rows):
            self.detail.setPlainText(json.dumps(self.rows[row], indent=2, ensure_ascii=False))
            if self.category.currentData() == "calibrations":
                identifier = self.rows[row]["calibration_id"]
                def received(record, error):
                    current = self.table.currentRow()
                    if not 0 <= current < len(self.rows) or self.rows[current].get("calibration_id") != identifier:
                        return
                    if error:
                        self.message.setText(str(error))
                    else:
                        self.detail.setPlainText(json.dumps(record, indent=2, ensure_ascii=False))
                self.operations.service.storage.submit("calibration.detail", {"id": identifier}, callback=received)

    def choose_export(self, format: str) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Exportar datos", f"reportes.{format}", f"{format.upper()} (*.{format})")
        if path:
            self.export_to(path, format)

    def export_to(self, path: str, format: str) -> None:
        try:
            filters = self.filters()
        except ValueError as exc:
            self.message.setText(str(exc))
            return
        self.message.setText("Exportando todas las filas filtradas fuera de UI…")
        self.operations.service.storage.submit("export", dict(category=self.category.currentData(), filters=filters,
                                                             path=path, format=format),
                                              callback=lambda count, error: self.message.setText(
                                                  f"Error de exportación: {error}" if error else f"Exportadas {count} filas a {path}."))

    def open_capture(self) -> None:
        row = self.table.currentRow()
        if self.category.currentData() != "captures" or not 0 <= row < len(self.rows):
            self.message.setText("Selecciona una captura.")
            return
        def opened(path, error):
            if error:
                self.message.setText(str(error))
            elif not QDesktopServices.openUrl(QUrl.fromLocalFile(path)):
                self.message.setText("El sistema no pudo abrir la captura.")
        self.operations.service.storage.submit("capture.open", {"path": self.rows[row]["relative_path"]}, callback=opened)
