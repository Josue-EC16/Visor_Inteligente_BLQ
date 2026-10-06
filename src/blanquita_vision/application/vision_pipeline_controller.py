import logging
from typing import Callable, Protocol

from ..domain.models.calibration import Calibration, CalibrationStatus
from ..domain.models.camera_state import CameraRuntimeState, CameraState
from ..domain.models.detection import DetectionParameters
from ..domain.models.vision_observation import VisionPipelineState
from .calibration_service import CalibrationService
from .camera_controller import CameraController
from .position_filter import EmaPositionFilter
from .vision_pipeline import ProcessedFrame

logger = logging.getLogger(__name__)


class VisionRunner(Protocol):
    @property
    def active(self) -> bool: ...

    def bind(self, event_handler: Callable, finished_handler: Callable) -> None: ...

    def start(self, parameters: DetectionParameters, alpha: float,
              calibration: Calibration | None, status: CalibrationStatus) -> None: ...

    def cancel(self) -> None: ...


class VisionPipelineController:
    def __init__(self, camera: CameraController, runner: VisionRunner,
                 calibration: CalibrationService) -> None:
        self.camera = camera
        self.runner = runner
        self.calibration = calibration
        self.state = VisionPipelineState.STOPPED
        self.parameters: DetectionParameters | None = None
        self.alpha: float | None = None
        self.last_error: str | None = None
        self.last_result: ProcessedFrame | None = None
        self.on_state: list[Callable[[], None]] = []
        self.on_result: list[Callable[[ProcessedFrame], None]] = []
        self._restart = False
        self._disposed = False
        self.start_source = "local_ui"
        self.stop_reason = "stop"
        runner.bind(self.handle_event, self.operation_finished)
        camera.on_state.append(self.camera_changed)
        calibration.on_change.append(self.calibration_changed)
        self.camera_changed(camera.runtime)

    def _notify(self) -> None:
        for callback in tuple(self.on_state):
            callback()

    def configure(self, parameters: DetectionParameters, alpha: float) -> None:
        EmaPositionFilter(alpha)
        self.parameters, self.alpha = parameters, alpha
        self.last_result = None
        if self.runner.active:
            self.stop(restart=True)
        else:
            self._notify()

    def start(self, source: str = "local_ui") -> None:
        if self.runner.active or self._disposed:
            return
        if self.camera.runtime.state is not CameraState.STREAMING or self.camera.store.latest() is None:
            raise ValueError("Conecta una cámara con video válido antes de iniciar el detector.")
        if self.parameters is None or self.alpha is None:
            raise ValueError("Introduce y aplica HSV, área, calidad mínima y alpha EMA.")
        if source not in ("local_ui", "mobile"):
            raise ValueError("Origen de inicio no válido.")
        self.start_source = source
        if self.state is VisionPipelineState.ERROR:
            self.state = VisionPipelineState.STOPPED
        self._restart = False
        self.last_error = None
        self.last_result = None
        self.state = VisionPipelineState.STARTING
        self._notify()
        try:
            self.runner.start(self.parameters, self.alpha, self.calibration.active(),
                              self.calibration.status)
        except Exception as exc:
            self.last_error = str(exc)
            self.state = VisionPipelineState.ERROR
            self._notify()

    def stop(self, restart: bool = False, reason: str = "local_stop") -> None:
        self._restart = restart and not self._disposed
        self.stop_reason = "reconfigure" if restart else reason
        if self.last_result is not None and self.last_result.observation.position is not None:
            logger.info("position_unavailable")
        self.last_result = None
        if self.runner.active:
            self.state = VisionPipelineState.STOPPING
            self.runner.cancel()
        else:
            self.state = VisionPipelineState.STOPPED
            self.last_error = None
        self._notify()

    def camera_changed(self, runtime: CameraRuntimeState) -> None:
        device = runtime.selected_device
        if device is not None:
            frame = self.camera.store.latest() if runtime.state is CameraState.STREAMING else None
            properties = runtime.properties
            width = frame.width if frame else properties.width if properties else None
            height = frame.height if frame else properties.height if properties else None
            self.calibration.observe_geometry(device.id, width, height)
        if runtime.state is not CameraState.STREAMING:
            if self.runner.active or self.last_result is not None or self._restart:
                self.stop()
        self._notify()

    def calibration_changed(self) -> None:
        self.last_result = None
        if self.runner.active:
            self.stop(restart=True)
        else:
            self._notify()

    def handle_event(self, kind: str, value=None) -> None:
        if self.state is VisionPipelineState.STOPPING or self._disposed:
            return
        if kind == "started":
            self.state = VisionPipelineState.RUNNING
            logger.info("vision_pipeline_started")
            logger.info("detector_started")
            self._notify()
        elif kind == "error":
            self.last_error = str(value)
            self.last_result = None
            self.state = VisionPipelineState.ERROR
            logger.error("vision_pipeline_error %s", value)
            self._notify()
        elif kind == "result" and self.state is VisionPipelineState.RUNNING:
            if value is not None and self.camera.runtime.state is CameraState.STREAMING:
                device = self.camera.runtime.selected_device
                if device is not None:
                    self.calibration.observe_geometry(device.id, value.frame.width, value.frame.height)
                if self.state is not VisionPipelineState.RUNNING:
                    return
                self.last_result = value
                for callback in tuple(self.on_result):
                    callback(value)

    def operation_finished(self) -> None:
        if self.state is not VisionPipelineState.ERROR:
            self.state = VisionPipelineState.STOPPED
        self.last_result = None
        logger.info("vision_pipeline_stopped")
        logger.info("detector_stopped")
        self._notify()
        restart, self._restart = self._restart, False
        if restart and self.camera.runtime.state is CameraState.STREAMING and not self._disposed:
            self.start(source=self.start_source)

    def dispose(self) -> None:
        self._disposed = True
        self.stop()
        if self.camera_changed in self.camera.on_state:
            self.camera.on_state.remove(self.camera_changed)
        if self.calibration_changed in self.calibration.on_change:
            self.calibration.on_change.remove(self.calibration_changed)
