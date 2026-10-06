from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class PlaceholderScreen(QWidget):
    def __init__(self, title: str, spec: str, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        heading = QLabel(title)
        heading.setObjectName("heading")
        layout.addWidget(heading)
        text = QLabel(f"Módulo preparado.\nLa funcionalidad se implementará en {spec}.")
        text.setWordWrap(True)
        layout.addWidget(text)
        layout.addStretch()
