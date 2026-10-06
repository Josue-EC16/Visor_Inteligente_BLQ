import json
import logging
from collections import deque
from datetime import datetime, timezone
from time import monotonic
from uuid import uuid4

from ..domain.models.calibration import CalibrationStatus
from ..domain.models.camera_state import CameraState
from ..domain.models.protocol import (
    CalibrationStatusPayload, CameraStatusPayload, ErrorPayload, ReadyPayload,
    StatusPayload, message, utc_text,
)
from ..domain.models.vision_observation import VisionPipelineState
from .report_mapper import millimeter_factor, report_from_observation

logger = logging.getLogger(__name__)


class MetricAggregator:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.start = datetime.now(timezone.utc)
        self.started = monotonic()
        self.sums, self.counts = {}, {}
        self.detections = self.lost = self.reacquired = self.errors = 0
        self.last_counts = (0, 0, 0)

    def add(self, result, capture_fps) -> None:
        metrics, observation = result.metrics, result.observation
        values = dict(capture_fps_avg=capture_fps, pipeline_fps_avg=metrics.pipeline_fps,
                      confidence_avg=observation.detection.confidence if observation.detection else None)
        for field in ("preprocess_ms", "detection_ms", "tracking_ms", "position_ms", "filter_ms", "total_ms"):
            values[field + "_avg"] = getattr(metrics, field)
        if (observation.position is not None and observation.position.calibrated
                and observation.calibration_status is CalibrationStatus.VALID
                and observation.detection is not None and observation.detection.detected):
            for prefix, position in (("raw", observation.position.raw_position), ("filtered", observation.position.filtered_position)):
                factor = millimeter_factor(position.unit)
                values[prefix + "_x_avg_mm"] = position.x * factor if position.x is not None else None
                values[prefix + "_y_avg_mm"] = position.y * factor if position.y is not None else None
        for key, value in values.items():
            if value is not None:
                self.sums[key] = self.sums.get(key, 0) + value
                self.counts[key] = self.counts.get(key, 0) + 1
        counts = (metrics.detections, metrics.lost_tracking, metrics.reacquisitions)
        changes = [max(0, current - previous) for current, previous in zip(counts, self.last_counts)]
        self.detections += changes[0]
        self.lost += changes[1]
        self.reacquired += changes[2]
        self.last_counts = counts

    def flush(self, session_id: str) -> dict:
        now = datetime.now(timezone.utc)
        record = dict(session_id=session_id, window_start_utc=utc_text(self.start), window_end_utc=utc_text(now),
                      detections_count=self.detections, tracking_lost_count=self.lost,
                      reacquisitions_count=self.reacquired, errors_count=self.errors)
        record.update({key: value / self.counts[key] for key, value in self.sums.items()})
        last = self.last_counts
        self.reset()
        self.last_counts = last
        return record


class OperationsService:
    def __init__(self, camera, vision, calibration, storage, network, calibration_repository,
                 system_snapshot: dict | None = None) -> None:
        self.camera, self.vision, self.calibration = camera, vision, calibration
        self.storage, self.network = storage, network
        self.calibration_repository = calibration_repository
        self.system_snapshot = system_snapshot or {}
        self.session_id = None
        self.session_source = "local_ui"
        self._previous_state = vision.state
        self._state_key = None
        self._load_key = None
        self._closing = False
        self._disposed = False
        self._health_requested = False
        self._last_health = 0.0
        self.errors = 0
        self.last_error = None
        self.on_change = []
        self.on_sample = []
        self.metrics = MetricAggregator()
        self.live_samples = deque()
        self.camera.on_state.append(self.state_changed)
        self.vision.on_state.append(self.state_changed)
        self.vision.on_result.append(self.observed)
        self.calibration.on_change.append(self.state_changed)
        storage.failure.connect(self.storage_failed)
        storage.on_ready.append(self.storage_ready)
        self.state_changed()

    def _changed(self) -> None:
        for callback in tuple(self.on_change):
            callback()

    def storage_ready(self) -> None:
        if self._closing:
            return
        self.storage.submit("settings.save", {"settings": self.storage.settings}, critical=True)
        self._event("storage", "database_opened", "Base de datos preparada.")
        self._changed()

    def storage_failed(self, error) -> None:
        self.errors += 1
        self.metrics.errors += 1
        self.last_error = str(error)
        logger.warning("storage_degraded %s", error)
        self._changed()

    def _event(self, category, kind, text, severity="INFO") -> None:
        if self._closing or self.storage.health["state"] not in ("READY", "DEGRADED"):
            return
        record = dict(session_id=self.session_id, timestamp_utc=utc_text(datetime.now(timezone.utc)),
                      category=category, event_type=kind, severity=severity, message=text)
        self.storage.submit("insert", {"table": "events", "record": record}, critical=True)

    def _error(self, component, code, text, recoverable=True) -> None:
        self.errors += 1
        self.metrics.errors += 1
        self.last_error = str(text)
        logger.error("%s %s", code, text)
        if not self._closing:
            self.network.server.publish_error(message("vision.error", ErrorPayload(code=code, message=str(text), recoverable=recoverable)))
            if self.storage.health["state"] in ("READY", "DEGRADED"):
                record = dict(session_id=self.session_id, timestamp_utc=utc_text(datetime.now(timezone.utc)),
                              component=component, code=code, message=str(text), recoverable=int(recoverable))
                self.storage.submit("insert", {"table": "errors", "record": record}, critical=True)
        self._changed()

    def ready(self) -> bool:
        return (self.camera.runtime.state is CameraState.STREAMING and self.camera.store.latest() is not None
                and self.vision.parameters is not None and self.vision.alpha is not None
                and self.vision.state not in (VisionPipelineState.ERROR, VisionPipelineState.STOPPING))

    def _snapshot(self):
        camera = self.camera.runtime
        calibration = self.calibration.active()
        observation = self.vision.last_result.observation if self.vision.last_result else None
        ready = ReadyPayload(ready=self.ready(), cameraState=camera.state.value,
                             pipelineState=self.vision.state.value, calibrationStatus=self.calibration.status.value)
        status = StatusPayload(cameraState=camera.state.value, pipelineState=self.vision.state.value,
                               calibrationStatus=self.calibration.status.value,
                               detectionState=observation.detection_state.value if observation else None,
                               trackingState=observation.tracking.state.value if observation and observation.tracking else None,
                               pipelineFps=self.vision.last_result.metrics.pipeline_fps if observation else None,
                               lastObservationTimestamp=observation.timestamp if observation else None)
        properties, device = camera.properties, camera.selected_device
        camera_payload = CameraStatusPayload(state=camera.state.value, cameraId=device.id if device else None,
                                             displayName=device.display_name if device else None,
                                             width=properties.width if properties else None, height=properties.height if properties else None,
                                             reportedFps=properties.reported_fps if properties else None)
        calibration_payload = CalibrationStatusPayload(status=self.calibration.status.value,
                                                       calibrationId=calibration.id if calibration else None,
                                                       cameraId=calibration.camera_id if calibration else None,
                                                       width=calibration.width if calibration else None,
                                                       height=calibration.height if calibration else None)
        return ready, status, camera_payload, calibration_payload

    def state_changed(self, *args) -> None:
        self.calibration_repository.geometry = self.calibration.geometry
        state = self.vision.state
        if state != self._previous_state:
            if self._previous_state is VisionPipelineState.RUNNING and self.session_id is not None:
                self._close_session("shutdown" if self._closing else "fatal_error" if state is VisionPipelineState.ERROR
                                    else "camera_unavailable" if self.camera.runtime.state is not CameraState.STREAMING
                                    else getattr(self.vision, "stop_reason", "stop"))
            if state is VisionPipelineState.RUNNING:
                self.session_id = str(uuid4())
                self.session_source = getattr(self.vision, "start_source", "local_ui")
                self.metrics.reset()
                properties = self.camera.runtime.properties
                device = self.camera.runtime.selected_device
                record = dict(session_id=self.session_id, started_at_utc=utc_text(datetime.now(timezone.utc)),
                              start_source=self.session_source, camera_id=device.id if device else None,
                              width=properties.width if properties else None, height=properties.height if properties else None)
                self.storage.submit("insert", {"table": "vision_sessions", "record": record}, critical=True)
                self._event("vision", "vision_pipeline_started", "Sesión de visión iniciada.")
            if state is not VisionPipelineState.RUNNING:
                self.network.server.clear_pending_report()
            if state is VisionPipelineState.ERROR and self.vision.last_error:
                self._error("vision", "vision_pipeline_error", self.vision.last_error)
            self._previous_state = state
        ready, status, camera, calibration = self._snapshot()
        self.network.server.update_snapshot(ready, status, camera, calibration)
        key = (ready.ready, camera.model_dump_json(), calibration.model_dump_json(), state.value,
               status.detectionState, status.trackingState)
        if key != self._state_key and not self._closing:
            self._state_key = key
            for kind, payload in (("vision.ready", ready), ("vision.status", status),
                                  ("camera.status", camera), ("calibration.status", calibration)):
                self.network.server.publish_status(message(kind, payload))
            self._event("state", "vision_status_changed", "Estado de visión/cámara/calibración actualizado.")
        self._changed()

    def _close_session(self, reason: str) -> None:
        if self.session_id is None:
            return
        if self.metrics.sums:
            self._flush_metrics()
        self.storage.submit("session.close", dict(id=self.session_id, timestamp=utc_text(datetime.now(timezone.utc)), reason=reason), critical=True)
        self.session_id = None

    def observed(self, result) -> None:
        if self._closing:
            return
        observation = result.observation
        try:
            detection, tracking, estimate = observation.detection, observation.tracking, observation.position
            record = dict(session_id=self.session_id, frame_sequence=observation.frame_sequence,
                          timestamp_utc=utc_text(observation.timestamp), detected=int(bool(detection and detection.detected)),
                          object_name="gancho", confidence=detection.confidence if detection else 0,
                          tracking_state=tracking.state.value if tracking else None,
                          tracking_source=tracking.source if tracking else None)
            if detection and detection.bounding_box:
                box = detection.bounding_box
                record.update(bbox_x=box.x, bbox_y=box.y, bbox_w=box.width, bbox_h=box.height,
                              centroid_u=detection.centroid.u, centroid_v=detection.centroid.v)
            if (estimate is not None and estimate.calibrated and detection is not None and detection.detected
                    and observation.calibration_status is CalibrationStatus.VALID):
                for prefix, position in (("raw", estimate.raw_position), ("filtered", estimate.filtered_position)):
                    factor = millimeter_factor(position.unit)
                    record[prefix + "_x_mm"] = position.x * factor if position.x is not None else None
                    record[prefix + "_y_mm"] = position.y * factor if position.y is not None else None
                calibration = self.calibration.active()
                record["calibration_id"] = calibration.id if calibration else None
            self.storage.submit("insert", {"table": "detections", "record": record})
            self.metrics.add(result, self.camera.store.metrics().measured_fps)
            if self.network.server.health()["client"]:
                report = report_from_observation(observation)
                self.network.server.publish_report(report, {"session_id": self.session_id})
        except (ValueError, TypeError) as exc:
            self._error("mapper", "observation_invalid", str(exc))
        self.state_changed()

    def _flush_metrics(self) -> None:
        if self.session_id is None:
            return
        sample = self.metrics.flush(self.session_id)
        self.storage.submit("insert", {"table": "metric_samples", "record": sample})
        self.live_samples.append(sample)
        cutoff = datetime.now(timezone.utc).timestamp() - 120
        while self.live_samples and datetime.fromisoformat(self.live_samples[0]["window_end_utc"]).timestamp() < cutoff:
            self.live_samples.popleft()
        for callback in tuple(self.on_sample):
            callback(sample)

    def tick(self) -> None:
        if self._closing:
            return
        for envelope in self.network.server.commands():
            error = None
            try:
                if envelope.type == "vision.start":
                    if self.vision.state is VisionPipelineState.STOPPING:
                        raise ValueError("Visión ocupada: deteniéndose.")
                    if self.vision.state not in (VisionPipelineState.STARTING, VisionPipelineState.RUNNING):
                        self.vision.start(source="mobile")
                else:
                    self.vision.stop(reason="mobile_stop")
                self._event("network", envelope.type, "Comando Mobile validado.")
            except ValueError as exc:
                error = str(exc)
            self.state_changed()
            self.network.server.complete_command(envelope, error)
        self.drain_network_events()
        if self.session_id is not None and monotonic() - self.metrics.started >= 1:
            self._flush_metrics()
        self._auto_load()
        if monotonic() - self._last_health >= 1 and not self._health_requested and self.storage.health["state"] in ("READY", "DEGRADED"):
            self._last_health = monotonic()
            self._health_requested = True
            self.storage.submit("health", {"capture_root": self.storage.settings["capture_root"]},
                                callback=self._health_received)
        self._changed()

    def drain_network_events(self) -> None:
        for event in self.network.server.events():
            if event["kind"] == "vision_report_sent":
                report = event["report"]
                payload, position = report.payload, report.payload.position
                record = dict(message_id=str(report.messageId), session_id=event["context"].get("session_id"),
                              frame_sequence=payload.frameSequence, envelope_timestamp_utc=utc_text(report.timestamp),
                              observation_timestamp_utc=utc_text(payload.observationTimestamp), detected=int(payload.detected),
                              object_name=payload.object, x_mm=position.x, y_mm=position.y, z_mm=None, angle=None,
                              confidence=payload.confidence, calibration_status=payload.calibrationStatus,
                              tracking_state=payload.trackingState, payload_json=report.model_dump_json())
                self.storage.submit("insert", {"table": "vision_reports", "record": record}, critical=True)
            elif "error" in event["kind"] or event["kind"] == "protocol_message_invalid":
                self._error("network", event["kind"], event.get("message", event["kind"]))
            else:
                self._event("network", event["kind"], event["kind"])

    def _health_received(self, result, error) -> None:
        self._health_requested = False

    def _auto_load(self) -> None:
        geometry = self.calibration.geometry
        if (self.camera.runtime.state is not CameraState.STREAMING or geometry is None
                or geometry == self._load_key or self.storage.health["state"] not in ("READY", "DEGRADED")):
            return
        self._load_key = geometry
        if self.calibration.active() is not None or self.calibration.status is CalibrationStatus.CALIBRATING:
            return
        revision = self.calibration.revision
        def loaded(candidate, error):
            if (self._closing or error or candidate is None or self.calibration.geometry != geometry
                    or self.calibration.revision != revision):
                return
            frame = self.camera.store.latest()
            device = self.camera.runtime.selected_device
            if (self.camera.runtime.state is not CameraState.STREAMING or frame is None or device is None
                    or (device.id, frame.width, frame.height) != geometry):
                return
            if self.calibration.status is CalibrationStatus.CALIBRATING:
                return
            try:
                self.calibration_repository.accept_loaded(candidate)
                self.calibration.apply(candidate)
                self._event("calibration", "calibration_loaded", "Perfil compatible cargado; verificar geometría física.")
            except ValueError as exc:
                self._error("calibration", "calibration_load_failed", str(exc))
        self.storage.submit("calibration.load", {"geometry": geometry}, callback=loaded)

    def capture(self, callback) -> None:
        try:
            captured = self.camera.capture()
            metadata = dict(session_id=self.session_id)
            result = self.vision.last_result
            if result is not None and (result.frame.sequence, result.frame.captured_at) == (captured.source_sequence, captured.captured_at):
                payload = report_from_observation(result.observation).payload
                metadata.update(detected=int(payload.detected), confidence=payload.confidence,
                                x_mm=payload.position.x, y_mm=payload.position.y, z_mm=None)
            self.storage.submit("capture", dict(capture=captured, format=self.storage.settings["capture_format"],
                                                root=self.storage.settings["capture_root"], metadata=metadata),
                                critical=True, callback=callback)
        except ValueError as exc:
            callback(None, str(exc))
        except Exception as exc:
            callback(None, str(exc))

    def begin_shutdown(self) -> None:
        if self._closing:
            return
        self._closing = True
        self.network.server.clear_pending_report()
        self.network.shutdown()
        self.drain_network_events()
        self._close_session("shutdown")

    def dispose(self) -> None:
        if self._disposed:
            return
        self._disposed = True
        for callbacks, callback in ((self.camera.on_state, self.state_changed), (self.vision.on_state, self.state_changed),
                                    (self.vision.on_result, self.observed), (self.calibration.on_change, self.state_changed)):
            if callback in callbacks:
                callbacks.remove(callback)
        if self.storage_ready in self.storage.on_ready:
            self.storage.on_ready.remove(self.storage_ready)
        self.storage.failure.disconnect(self.storage_failed)
