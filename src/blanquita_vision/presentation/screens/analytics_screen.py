from datetime import datetime

import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import QLabel, QTabWidget, QVBoxLayout, QWidget

from .record_browser import COLUMN_LABELS, RecordBrowser


class MetricCharts(pg.GraphicsLayoutWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setBackground("#08090b")
        self.curves = {}
        definitions = [
            ("FPS", ("capture_fps_avg", "pipeline_fps_avg")),
            ("Latencias (ms)", ("preprocess_ms_avg", "detection_ms_avg", "tracking_ms_avg", "position_ms_avg", "filter_ms_avg", "total_ms_avg")),
            ("Calidad y conteos", ("confidence_avg", "detections_count", "tracking_lost_count", "reacquisitions_count", "errors_count")),
            ("Posición (mm), Z no disponible", ("raw_x_avg_mm", "raw_y_avg_mm", "filtered_x_avg_mm", "filtered_y_avg_mm")),
        ]
        colors = ("#79e2a4", "#ffcf66", "#76baff", "#ff8585", "#e0aaff", "#ffffff")
        for row, (title, fields) in enumerate(definitions):
            plot = self.addPlot(row=row // 2, col=row % 2, title=title,
                                axisItems={"bottom": pg.DateAxisItem()})
            plot.addLegend()
            plot.showGrid(x=True, y=True, alpha=0.2)
            for index, field in enumerate(fields):
                self.curves[field] = plot.plot(name=COLUMN_LABELS.get(field, field), pen=pg.mkPen(colors[index % len(colors)], width=2))

    def update_rows(self, rows) -> None:
        rows = sorted(rows, key=lambda row: row["window_end_utc"])
        x = [datetime.fromisoformat(row["window_end_utc"]).timestamp() for row in rows]
        for field, curve in self.curves.items():
            y = [row.get(field) if row.get(field) is not None else np.nan for row in rows]
            curve.setData(x, y, connect="finite")


class AnalyticsScreen(QWidget):
    def __init__(self, parent=None, operations=None) -> None:
        super().__init__(parent)
        self.operations = operations
        layout = QVBoxLayout(self)
        title = QLabel("ANALÍTICA")
        title.setObjectName("heading")
        layout.addWidget(title)
        if operations is None:
            layout.addWidget(QLabel("Módulo preparado para SPEC-02."))
            layout.addStretch()
            return
        tabs = QTabWidget()
        realtime = QWidget()
        realtime_layout = QVBoxLayout(realtime)
        realtime_layout.addWidget(QLabel("Últimos 120 s · Agregados por segundo · Calidad no es probabilidad"))
        self.live = MetricCharts()
        realtime_layout.addWidget(self.live)
        historical = QWidget()
        history_layout = QVBoxLayout(historical)
        history_layout.addWidget(QLabel("Histórico por sesión/rango. Las series muestran la página consultada de 50 filas."))
        self.history = MetricCharts()
        self.browser = RecordBrowser(operations, {"Muestras métricas": "metric_samples"})
        history_layout.addWidget(self.history, 1)
        history_layout.addWidget(self.browser, 1)
        self.browser.on_rows.append(self.history.update_rows)
        tabs.addTab(realtime, "TIEMPO REAL")
        tabs.addTab(historical, "HISTÓRICO")
        layout.addWidget(tabs)
        operations.service.on_sample.append(self.sampled)

    def sampled(self, sample) -> None:
        self.live.update_rows(list(self.operations.service.live_samples))

    def dispose(self) -> None:
        if self.operations is not None and self.sampled in self.operations.service.on_sample:
            self.operations.service.on_sample.remove(self.sampled)
