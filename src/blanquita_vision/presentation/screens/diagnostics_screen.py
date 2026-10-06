from dataclasses import asdict
from datetime import datetime

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QLabel, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

class DiagnosticsScreen(QWidget):
    def __init__(self, parent=None, operations=None) -> None:
        super().__init__(parent)
        self.operations = operations
        layout = QVBoxLayout(self)
        title = QLabel("DIAGNÓSTICOS")
        title.setObjectName("heading")
        layout.addWidget(title)
        if operations is None:
            layout.addWidget(QLabel("Módulo preparado para SPEC-02."))
            layout.addStretch()
            return
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Componente / dato", "Valor"])
        layout.addWidget(self.tree)
        layout.addWidget(QLabel("Heartbeat: 2 s · Stale Mobile: 6 s · Duración de envío no equivale a RTT."))
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.refresh)
        self.timer.start()
        self.refresh()

    def refresh(self) -> None:
        service = self.operations.service
        runtime, vision = service.camera.runtime, service.vision
        snapshot = {
            "CAMERA": dict(state=runtime.state.value, device=runtime.selected_device.display_name if runtime.selected_device else None,
                           backend=runtime.properties.backend_name if runtime.properties else None,
                           resolution=f"{runtime.properties.width}×{runtime.properties.height}" if runtime.properties else None,
                           reported_fps=runtime.properties.reported_fps if runtime.properties else None,
                           measured_fps=service.camera.store.metrics().measured_fps),
            "VISION": dict(pipeline=vision.state.value, calibration=service.calibration.status.value,
                           last_error=vision.last_error, session_id=service.session_id,
                           pipeline_fps=vision.last_result.metrics.pipeline_fps if vision.last_result else None,
                           total_ms=vision.last_result.metrics.total_ms if vision.last_result else None),
            "NETWORK": service.network.server.health(),
            "DATABASE": service.storage.health,
            "FILESYSTEM": dict(path=service.storage.settings["capture_root"], format=service.storage.settings["capture_format"],
                               writable=service.storage.health.get("capture_writable"), last_capture=service.storage.health.get("last_capture")),
            "SYSTEM": service.system_snapshot,
        }
        self.tree.clear()
        for group, values in snapshot.items():
            parent = QTreeWidgetItem([group, ""])
            self.tree.addTopLevelItem(parent)
            for key, value in values.items():
                if key in ("settings",):
                    continue
                if isinstance(value, str) and value.endswith("Z"):
                    try:
                        value = datetime.fromisoformat(value).astimezone().isoformat(timespec="seconds")
                    except ValueError:
                        pass
                parent.addChild(QTreeWidgetItem([key, "No disponible" if value is None else str(value)]))
            parent.setExpanded(True)
            if group == "NETWORK" and service.discovery is not None:
                discovery = service.discovery.snapshot()
                child = QTreeWidgetItem(["UDP DISCOVERY", discovery.state.value])
                parent.addChild(child)
                for key, value in asdict(discovery).items():
                    if key == "state":
                        continue
                    child.addChild(QTreeWidgetItem([key, "No disponible" if value is None else str(value)]))
                child.setExpanded(True)

    def dispose(self) -> None:
        if hasattr(self, "timer"):
            self.timer.stop()
