import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import QGraphicsRectItem

from ...domain.models.frame import Frame
from ...domain.models.geometry import BoundingBox, ImagePoint


class VideoWidget(pg.GraphicsLayoutWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setBackground("#000000")
        self.view = self.addViewBox(lockAspect=True, enableMenu=False)
        self.view.invertY(True)
        self.image_item = pg.ImageItem(axisOrder="row-major")
        self.view.addItem(self.image_item)
        self.box_item = QGraphicsRectItem()
        self.box_item.setPen(pg.mkPen("#79e2a4", width=2))
        self.view.addItem(self.box_item)
        self.center_item = pg.ScatterPlotItem(size=8, brush="#ffcf66", pen=None)
        self.view.addItem(self.center_item)
        self.overlay_label = pg.TextItem(color="#79e2a4", anchor=(0, 1))
        self.view.addItem(self.overlay_label)
        self.clear_overlay()
        self.view.setMouseEnabled(x=False, y=False)
        self._shape = None

    def render(self, frame: Frame) -> None:
        image = np.asarray(frame.image)
        if image.ndim == 3:
            if image.shape[2] == 3:
                image = np.ascontiguousarray(image[:, :, ::-1])
            elif image.shape[2] == 4:
                image = np.ascontiguousarray(image[:, :, [2, 1, 0, 3]])
            elif image.shape[2] == 1:
                image = image[:, :, 0]
            else:
                raise ValueError("Formato de imagen no compatible.")
        elif image.ndim != 2:
            raise ValueError("Formato de imagen no compatible.")
        self.image_item.setImage(image, autoLevels=False, levels=(0, 255))
        shape = (frame.width, frame.height)
        if shape != self._shape:
            self.view.setRange(xRange=(0, frame.width), yRange=(0, frame.height),
                               padding=0)
            self._shape = shape

    def clear_frame(self) -> None:
        self.image_item.clear()
        self._shape = None
        self.clear_overlay()

    def set_overlay(self, box: BoundingBox | None, center: ImagePoint | None,
                    text: str = "") -> None:
        if box is None or center is None:
            self.clear_overlay()
            return
        self.box_item.setRect(box.x, box.y, box.width, box.height)
        self.box_item.show()
        self.center_item.setData([center.u], [center.v])
        self.center_item.show()
        self.overlay_label.setText(text)
        self.overlay_label.setPos(box.x, box.y)
        self.overlay_label.show()

    def clear_overlay(self) -> None:
        self.box_item.hide()
        self.center_item.hide()
        self.overlay_label.hide()
