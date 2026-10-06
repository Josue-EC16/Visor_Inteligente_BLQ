import cv2
import numpy as np
import pytest

from blanquita_vision.adapters.camera.opencv_camera import OpenCvCamera
from blanquita_vision.domain.models.camera_state import CameraError
from blanquita_vision.domain.models.capture_configuration import CaptureConfiguration


class CaptureDouble:
    def __init__(self, opened=True, image=None, fps=25.0):
        self.opened = opened
        self.image = image if image is not None else np.zeros((12, 16, 3), np.uint8)
        self.fps = fps
        self.set_calls = []
        self.releases = 0

    def isOpened(self):
        return self.opened

    def get(self, key):
        return {cv2.CAP_PROP_FRAME_WIDTH: 16, cv2.CAP_PROP_FRAME_HEIGHT: 12,
                cv2.CAP_PROP_FPS: self.fps}.get(key, 0)

    def set(self, key, value):
        self.set_calls.append((key, value))
        return True

    def getBackendName(self):
        return "DOUBLE"

    def read(self):
        return True, self.image

    def release(self):
        self.releases += 1
        self.opened = False


def test_discovery_closes_temporaries_and_handles_sparse_indices():
    captures = []

    def factory(index, backend):
        assert backend == cv2.CAP_ANY
        capture = CaptureDouble(opened=index in (0, 2))
        captures.append(capture)
        return capture

    camera = OpenCvCamera((0, 1, 2), capture_factory=factory)
    assert [device.index for device in camera.discover()] == [0, 2]
    assert all(capture.releases == 1 for capture in captures)


def test_discovery_continues_after_index_error():
    def factory(index, backend):
        if index == 0:
            raise OSError("dispositivo inaccesible")
        return CaptureDouble()

    camera = OpenCvCamera((0, 1), capture_factory=factory)
    assert [device.index for device in camera.discover()] == [1]


def test_tc_008_no_forced_resolution_or_fps_and_tc_009_properties():
    capture = CaptureDouble()
    camera = OpenCvCamera(capture_factory=lambda *args: capture)
    properties = camera.open(CaptureConfiguration(0))
    assert capture.set_calls == []
    assert (properties.width, properties.height, properties.reported_fps) == (16, 12, 25.0)
    frame = camera.read()
    assert frame.captured_at.tzinfo is not None
    assert not frame.image.flags.writeable
    capture.image[:] = 255
    assert np.all(frame.image == 0)
    camera.close()
    camera.close()
    assert capture.releases == 1


@pytest.mark.parametrize("fps", [0.0, float("nan"), float("inf"), -1.0])
def test_unreliable_fps_is_unavailable(fps):
    capture = CaptureDouble(fps=fps)
    camera = OpenCvCamera(capture_factory=lambda *args: capture)
    assert camera.open(CaptureConfiguration(0)).reported_fps is None
    camera.close()


def test_tc_007_open_failure_releases_resource():
    capture = CaptureDouble(opened=False)
    camera = OpenCvCamera(capture_factory=lambda *args: capture)
    with pytest.raises(CameraError):
        camera.open(CaptureConfiguration(0))
    assert not camera.is_open
    assert capture.releases == 1


@pytest.mark.parametrize("image", [np.empty((0, 0, 3), np.uint8),
                                   np.zeros((12, 16, 2), np.uint8),
                                   np.zeros((12, 16, 3), np.float32)])
def test_tc_011_invalid_frame_not_published(image):
    capture = CaptureDouble(image=image)
    camera = OpenCvCamera(capture_factory=lambda *args: capture)
    camera.open(CaptureConfiguration(0))
    assert camera.read() is None
    camera.close()


def test_backend_unknown_is_explicit_error():
    camera = OpenCvCamera()
    with pytest.raises(CameraError, match="Backend"):
        camera.open(CaptureConfiguration(0, "DOES_NOT_EXIST"))


@pytest.mark.parametrize("operation", ["discover", "open"])
def test_registered_but_unavailable_backend_fails_before_camera_probe(monkeypatch, operation):
    monkeypatch.setattr(cv2.videoio_registry, "getBackends", lambda: (cv2.CAP_MSMF,))
    monkeypatch.setattr(cv2.videoio_registry, "hasBackend", lambda backend: False)
    calls = []

    def factory(index, backend):
        calls.append((index, backend))
        return CaptureDouble()

    camera = OpenCvCamera(backend="MSMF", capture_factory=factory)
    with pytest.raises(CameraError, match="MSMF no disponible") as error:
        if operation == "discover":
            camera.discover()
        else:
            camera.open(CaptureConfiguration(0, "MSMF"))
    assert error.value.code == "backend_unavailable"
    assert calls == []
    assert not camera.is_open


def test_explicit_available_backend_is_preserved(monkeypatch):
    monkeypatch.setattr(cv2.videoio_registry, "getBackends", lambda: (cv2.CAP_DSHOW,))
    monkeypatch.setattr(cv2.videoio_registry, "hasBackend", lambda backend: backend == cv2.CAP_DSHOW)
    calls = []
    capture = CaptureDouble()

    def factory(index, backend):
        calls.append((index, backend))
        return capture

    camera = OpenCvCamera(capture_factory=factory)
    camera.open(CaptureConfiguration(0, "DSHOW"))
    assert calls == [(0, cv2.CAP_DSHOW)]
    camera.close()


def test_close_failure_is_logged_and_logically_closed(caplog):
    capture = CaptureDouble()
    camera = OpenCvCamera(capture_factory=lambda *args: capture)
    camera.open(CaptureConfiguration(0))

    def fail_release():
        raise OSError("fallo del driver")

    capture.release = fail_release
    camera.close()
    assert not camera.is_open
    assert "camera_release_failed" in caplog.text
