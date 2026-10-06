import pytest

from blanquita_vision.adapters.camera.opencv_camera import OpenCvCamera
from blanquita_vision.domain.models.capture_configuration import CaptureConfiguration


@pytest.mark.hardware
def test_tc_021_real_camera_frames_and_release(request):
    index = request.config.getoption("--hardware-camera-index")
    if index is None:
        pytest.skip("Hardware pendiente: indicar --hardware-camera-index N para ejecutar.")
    camera = OpenCvCamera()
    try:
        camera.open(CaptureConfiguration(index))
        frame = camera.read()
        assert frame is not None
        assert frame.width > 0 and frame.height > 0
    finally:
        camera.close()
    assert not camera.is_open
