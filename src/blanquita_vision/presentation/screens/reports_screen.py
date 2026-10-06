from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget
from .record_browser import RecordBrowser


class ReportsScreen(QWidget):
    def __init__(self, parent=None, operations=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        title = QLabel("REPORTES")
        title.setObjectName("heading")
        layout.addWidget(title)
        if operations is None:
            layout.addWidget(QLabel("Módulo preparado para SPEC-02."))
            layout.addStretch()
        else:
            self.browser = RecordBrowser(operations)
            layout.addWidget(self.browser)
