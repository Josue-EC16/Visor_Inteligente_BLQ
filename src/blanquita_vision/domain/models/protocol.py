import json
from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, PlainSerializer, field_validator, model_validator


def utc_text(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Timestamp requiere zona horaria.")
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


UtcDatetime = Annotated[AwareDatetime, PlainSerializer(utc_text, return_type=str, when_used="json")]


class StrictModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", allow_inf_nan=False, populate_by_name=True)


class PositionPayload(StrictModel):
    x: float | None = None
    y: float | None = None
    z: None = None
    angle: None = None
    unit: Literal["mm"] = "mm"


class ReportPayload(StrictModel):
    detected: bool
    object: Literal["gancho"] = "gancho"
    position: PositionPayload
    confidence: float = Field(ge=0, le=1)
    calibrationStatus: Literal["UNCALIBRATED", "CALIBRATING", "VALID", "INVALID", "ERROR"]
    trackingState: Literal["INACTIVE", "INITIALIZING", "TRACKING", "LOST", "ERROR"]
    frameSequence: int = Field(ge=0)
    observationTimestamp: UtcDatetime

    @model_validator(mode="after")
    def check_position(self):
        if not self.detected or self.calibrationStatus != "VALID":
            if self.position.x is not None or self.position.y is not None:
                raise ValueError("Posición física requiere detección y calibración válidas.")
        if (self.position.x is None) != (self.position.y is None):
            raise ValueError("X/Y deben estar disponibles conjuntamente.")
        return self


class HelloPayload(StrictModel):
    server: Literal["BLANQUITA Vision"] = "BLANQUITA Vision"
    protocolVersion: Literal[1] = 1
    endpoint: Literal["/vision"] = "/vision"


class ReadyPayload(StrictModel):
    ready: bool
    cameraState: str
    pipelineState: str
    calibrationStatus: str


class StatusPayload(StrictModel):
    cameraState: str
    pipelineState: str
    detectionState: str | None = None
    trackingState: str | None = None
    calibrationStatus: str
    pipelineFps: float | None = Field(default=None, ge=0)
    lastObservationTimestamp: UtcDatetime | None = None


class ErrorPayload(StrictModel):
    code: str
    message: str
    recoverable: bool
    replyToMessageId: UUID | None = None


class HeartbeatPayload(StrictModel):
    serverTime: UtcDatetime
    ready: bool
    replyToMessageId: UUID | None = None


class CameraStatusPayload(StrictModel):
    state: str
    cameraId: str | None = None
    displayName: str | None = None
    width: int | None = Field(default=None, gt=0)
    height: int | None = Field(default=None, gt=0)
    reportedFps: float | None = Field(default=None, gt=0)


class CalibrationStatusPayload(StrictModel):
    status: str
    calibrationId: str | None = None
    unit: Literal["mm"] = "mm"
    cameraId: str | None = None
    width: int | None = Field(default=None, gt=0)
    height: int | None = Field(default=None, gt=0)


class EmptyPayload(StrictModel):
    pass


PAYLOAD_MODELS = {
    "vision.hello": HelloPayload, "vision.ready": ReadyPayload, "vision.status": StatusPayload,
    "vision.report": ReportPayload, "vision.error": ErrorPayload, "vision.heartbeat": HeartbeatPayload,
    "camera.status": CameraStatusPayload, "calibration.status": CalibrationStatusPayload,
    "vision.start": EmptyPayload, "vision.stop": EmptyPayload, "vision.ping": EmptyPayload,
}


class ProtocolEnvelope(StrictModel):
    protocol: Literal["blanquita-vision"]
    version: Literal[1]
    type: str
    messageId: UUID
    timestamp: UtcDatetime
    payload: HelloPayload | ReadyPayload | StatusPayload | ReportPayload | ErrorPayload | HeartbeatPayload | CameraStatusPayload | CalibrationStatusPayload | EmptyPayload

    @field_validator("version", mode="before")
    @classmethod
    def integer_version(cls, value):
        if type(value) is not int or value != 1:
            raise ValueError("Versión incompatible.")
        return value

    @field_validator("payload", mode="before")
    @classmethod
    def parse_typed_payload(cls, value, info):
        expected = PAYLOAD_MODELS.get(info.data.get("type"))
        if expected is None:
            raise ValueError("Tipo de mensaje no admitido.")
        if isinstance(value, expected):
            return value
        if not isinstance(value, dict):
            raise ValueError("Payload debe ser un objeto JSON.")
        return expected.model_validate_json(json.dumps(value, allow_nan=False))

    @model_validator(mode="after")
    def matching_payload(self):
        expected = PAYLOAD_MODELS.get(self.type)
        if expected is None or not isinstance(self.payload, expected):
            raise ValueError("Tipo de mensaje o payload incompatible.")
        return self


def message(kind: str, payload: BaseModel) -> ProtocolEnvelope:
    return ProtocolEnvelope(protocol="blanquita-vision", version=1, type=kind,
                            messageId=uuid4(), timestamp=datetime.now(timezone.utc), payload=payload)


def parse_command(text: str) -> ProtocolEnvelope:
    envelope = ProtocolEnvelope.model_validate_json(text)
    if envelope.type not in ("vision.start", "vision.stop", "vision.ping"):
        raise ValueError("Mensaje no permitido desde Mobile.")
    return envelope
