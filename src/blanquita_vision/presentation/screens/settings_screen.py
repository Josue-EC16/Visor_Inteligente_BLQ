import logging

from PySide6.QtWidgets import QComboBox, QFileDialog, QFormLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget


class SettingsScreen(QWidget):
    def __init__(self, parent=None, operations=None) -> None:
        super().__init__(parent)
        self.operations = operations
        self._populated = False
        layout = QVBoxLayout(self)
        title = QLabel("AJUSTES")
        title.setObjectName("heading")
        layout.addWidget(title)
        if operations is None:
            layout.addWidget(QLabel("Módulo preparado para SPEC-02."))
            layout.addStretch()
            return
        self.format = QComboBox()
        self.format.addItem("JPEG", "jpg")
        self.format.addItem("PNG", "png")
        self.root = QLineEdit()
        self.log_level = QComboBox()
        self.log_level.addItems(["INFO", "WARNING", "ERROR"])
        form = QFormLayout()
        form.addRow("Formato de captura manual", self.format)
        form.addRow("Ruta de capturas", self.root)
        form.addRow("Nivel de logs", self.log_level)
        layout.addLayout(form)
        choose = QPushButton("Elegir carpeta de capturas")
        choose.clicked.connect(self.choose_root)
        self.apply_button = QPushButton("Guardar ajustes")
        self.apply_button.clicked.connect(self.apply)
        layout.addWidget(choose)
        layout.addWidget(self.apply_button)
        self.paths = QLabel()
        self.paths.setWordWrap(True)
        layout.addWidget(self.paths)
        note = QLabel("La ruta de datos se selecciona al arrancar con --data-dir. "
                      "Endpoint fijo 0.0.0.0:8765/vision · ws:// sin autenticación, solo LAN privada. "
                      "Sin borrado automático de históricos/capturas.")
        note.setWordWrap(True)
        layout.addWidget(note)
        self.message = QLabel()
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        layout.addStretch()
        operations.service.storage.changed.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        storage = self.operations.service.storage
        self.paths.setText(f"DB: {storage.health['path']}\nEstado: {storage.health['state']} · "
                           f"WAL: {storage.health.get('wal', 'No disponible')} · Schema: {storage.health.get('schema_version', 'No disponible')}")
        if not self._populated and storage.health["state"] in ("READY", "DEGRADED"):
            self._populated = True
            self.format.setCurrentIndex(self.format.findData(storage.settings["capture_format"]))
            self.root.setText(storage.settings["capture_root"])
            self.log_level.setCurrentText(storage.settings["log_level"])

    def choose_root(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Carpeta de capturas", self.root.text())
        if path:
            self.root.setText(path)

    def apply(self) -> None:
        settings = dict(capture_format=self.format.currentData(), capture_root=self.root.text().strip(),
                        log_level=self.log_level.currentText())
        self.message.setText("Guardando ajustes fuera de UI…")
        def saved(result, error):
            if error:
                self.message.setText(f"Ajustes no guardados: {error}")
            else:
                logging.getLogger().setLevel(result["log_level"])
                self.message.setText("Ajustes guardados; se aplican a las siguientes capturas.")
        self.operations.service.storage.submit("settings.save", {"settings": settings}, critical=True, callback=saved)
