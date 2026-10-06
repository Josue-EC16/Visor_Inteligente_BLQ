import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from blanquita_vision.application.report_mapper import calibration_in_mm, millimeter_factor, report_from_observation
from blanquita_vision.domain.models.calibration import CalibrationStatus
from blanquita_vision.domain.models.position import SpatialPosition
from blanquita_vision.domain.models.protocol import EmptyPayload, PositionPayload, ProtocolEnvelope, message, parse_command, utc_text
from tests.unit.test_calibration_position_filter import calibrated_service
from tests.unit.test_vision_pipeline import pipeline
from tests.fixtures.vision_fakes import color_frame


def command_dict():
    return json.loads(message("vision.start", EmptyPayload()).model_dump_json())


def test_valid_command_and_canonical_utc_uuid():
    raw = command_dict()
    envelope = parse_command(json.dumps(raw))
    assert envelope.type == "vision.start"
    assert envelope.payload == EmptyPayload()
    assert raw["timestamp"].endswith("Z")
    assert str(envelope.messageId) == raw["messageId"]


@pytest.mark.parametrize("change", [
    {"protocol": "other"}, {"version": 2}, {"version": True}, {"version": 1.0},
    {"messageId": "invalid"}, {"timestamp": "2026-10-06T12:00:00"},
    {"type": "motor.move"}, {"payload": {"command": "d"}}, {"command": "d"},
    {"type": "vision.pong"}, {"payload": None},
])
def test_invalid_commands_do_not_parse(change):
    raw = command_dict()
    raw.update(change)
    with pytest.raises((ValidationError, ValueError)):
        parse_command(json.dumps(raw))


@pytest.mark.parametrize("key", ["protocol", "version", "type", "messageId", "timestamp", "payload"])
def test_every_envelope_field_is_required(key):
    raw = command_dict()
    raw.pop(key)
    with pytest.raises(ValidationError):
        parse_command(json.dumps(raw))


def test_aware_offset_normalizes_to_utc():
    raw = command_dict()
    raw["timestamp"] = "2026-10-06T12:30:00.123-04:00"
    envelope = parse_command(json.dumps(raw))
    assert json.loads(envelope.model_dump_json())["timestamp"] == "2026-10-06T16:30:00.123Z"
    with pytest.raises(ValueError):
        utc_text(datetime(2026, 10, 6))


def test_report_uses_filtered_mm_and_frame_timestamp():
    observation = pipeline().process(color_frame(7)).observation
    position = replace(observation.position, filtered_position=SpatialPosition(12, 34, None, "cm"))
    report = report_from_observation(replace(observation, position=position))
    assert (report.payload.position.x, report.payload.position.y) == (120, 340)
    assert report.payload.position.z is None
    assert report.payload.position.angle is None
    assert report.payload.frameSequence == 7
    assert report.payload.observationTimestamp == observation.timestamp
    assert report.payload.position.unit == "mm"
    assert ProtocolEnvelope.model_validate_json(report.model_dump_json()).type == "vision.report"


@pytest.mark.parametrize("calibrated,detected", [(False, True), (True, False)])
def test_unavailable_position_never_reuses_previous_coordinates(calibrated, detected):
    observation = pipeline().process(color_frame()).observation
    detection = replace(observation.detection, detected=detected)
    report = report_from_observation(replace(observation, detection=detection,
                                            calibration_status=CalibrationStatus.VALID if calibrated else CalibrationStatus.INVALID))
    assert report.payload.detected is detected
    assert report.payload.position.x is None
    assert report.payload.position.y is None


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_protocol_rejects_nonfinite_coordinates(value):
    with pytest.raises(ValidationError):
        PositionPayload(x=value, y=0.0)


def test_unit_conversion_preserves_homography_mapping():
    service, calibration = calibrated_service()
    points = tuple(replace(point, physical=replace(point.physical, x=point.physical.x / 10,
                                                   y=point.physical.y / 10, unit="cm")) for point in calibration.points)
    matrix = tuple(tuple(value / 10 if row < 2 else value for value in values)
                   for row, values in enumerate(calibration.homography))
    converted = calibration_in_mm(replace(calibration, unit="cm", points=points, homography=matrix))
    assert converted.points == calibration.points
    for original_row, converted_row in zip(calibration.homography, converted.homography):
        assert converted_row == pytest.approx(original_row)
    assert millimeter_factor("m") == 1000
    with pytest.raises(ValueError):
        millimeter_factor("unknown")
