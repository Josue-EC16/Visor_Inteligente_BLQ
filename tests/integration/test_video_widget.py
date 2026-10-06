import numpy as np

from blanquita_vision.domain.models.frame import Frame
from blanquita_vision.presentation.widgets.video_widget import VideoWidget
from tests.fixtures.fake_camera import make_frame


def test_bgr_to_rgb_without_rotation_or_mutating_source(qapp):
    image = np.zeros((12, 16, 3), np.uint8)
    image[0, 0] = [10, 20, 30]
    sample = make_frame()
    frame = Frame(0, sample.captured_at, 16, 12, image)
    widget = VideoWidget()
    widget.render(frame)
    assert widget.image_item.image.shape == (12, 16, 3)
    assert list(widget.image_item.image[0, 0]) == [30, 20, 10]
    assert list(image[0, 0]) == [10, 20, 30]
    widget.clear_frame()
    assert widget.image_item.image is None
    widget.close()
