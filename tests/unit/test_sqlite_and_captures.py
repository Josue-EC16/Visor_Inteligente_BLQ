import json
import sqlite3
from datetime import datetime, timezone

import cv2
import numpy as np
import pytest

from blanquita_vision.adapters.storage.filesystem_capture_storage import FileSystemCaptureStorage, resolve_capture_path
from blanquita_vision.adapters.storage.sqlite_vision_repository import SQLiteVisionRepository
from blanquita_vision.domain.models.frame import CapturedFrame
from blanquita_vision.domain.models.protocol import utc_text
from tests.fixtures.vision_fakes import color_frame
from tests.unit.test_calibration_position_filter import calibrated_service


@pytest.fixture
def repository(tmp_path):
    repo = SQLiteVisionRepository(tmp_path / "data.db")
    repo.open()
    yield repo
    repo.close()


def session_record(identifier="session"):
    return dict(session_id=identifier, started_at_utc="2026-10-06T12:00:00.000Z", start_source="local_ui")


def test_schema_wal_foreign_keys_and_no_blob(repository):
    assert repository.health()["wal"] == "wal"
    assert repository.connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert repository.health()["schema_version"] == 1
    assert len(repository.columns) == 10
    with pytest.raises(sqlite3.IntegrityError):
        repository.save_detection(dict(session_id="missing", frame_sequence=1, timestamp_utc="2026-10-06T12:00:00Z",
                                       detected=0, object_name="gancho", confidence=0))
    assert not any("BLOB" in row[2].upper() for row in repository.connection.execute("PRAGMA table_info(captures)"))


def test_session_lifecycle_filters_and_pagination(repository):
    for index in range(55):
        repository.create_session(session_record(str(index)))
    assert len(repository.query("vision_sessions", {}, 50, 0)) == 50
    assert len(repository.query("vision_sessions", {}, 50, 50)) == 5
    repository.close_session("0", "2026-10-06T12:01:00Z", "mobile_stop")
    record = repository.query("vision_sessions", {"session_id": "0"}, 50, 0)[0]
    assert record["end_reason"] == "mobile_stop"
    assert record["ended_at_utc"].endswith("Z")
    assert repository.query("vision_sessions", {"session_id": "' OR 1=1 --"}, 50, 0) == []
    with pytest.raises(ValueError):
        repository.query("vision_sessions; DROP TABLE errors", {}, 50, 0)


def test_calibration_four_points_reload_and_invalidation(repository):
    service, calibration = calibrated_service()
    repository.save_calibration(calibration)
    loaded = repository.load_calibration("0", 160, 120)
    assert loaded.id == calibration.id
    assert loaded.points == calibration.points
    assert loaded.unit == "mm"
    assert len(repository.calibration_details(loaded.id)["points"]) == 4
    assert repository.load_calibration("1", 160, 120) is None
    assert repository.load_calibration("0", 320, 240) is None
    repository.invalidate_calibration(calibration.id, "2026-10-06T13:00:00Z")
    assert repository.load_calibration("0", 160, 120) is None
    assert repository.query("calibrations", {}, 50, 0)[0]["status"] == "INVALID"


def test_corrupt_or_future_database_has_explicit_error(tmp_path):
    path = tmp_path / "future.db"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE schema_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
        connection.execute("INSERT INTO schema_meta VALUES('schema_version','99')")
    before = path.read_bytes()
    repo = SQLiteVisionRepository(path)
    with pytest.raises(ValueError, match="incompatible"):
        repo.open()
    assert path.read_bytes() == before
    corrupt = tmp_path / "corrupt.db"
    corrupt.write_bytes(b"not a database")
    with pytest.raises(sqlite3.DatabaseError):
        SQLiteVisionRepository(corrupt).open()


def test_settings_and_exports_preserve_null_utc_and_columns(repository, tmp_path):
    repository.save_settings({"capture_format": "png"})
    assert repository.load_settings()["capture_format"] == "png"
    repository.create_session(session_record())
    json_path, csv_path = tmp_path / "sessions.json", tmp_path / "sessions.csv"
    assert repository.export("vision_sessions", {}, json_path, "json") == 1
    assert repository.export("vision_sessions", {}, csv_path, "csv") == 1
    row = json.loads(json_path.read_text(encoding="utf-8"))[0]
    assert row["ended_at_utc"] is None
    assert row["started_at_utc"].endswith("Z")
    assert csv_path.read_text(encoding="utf-8").startswith("session_id,started_at_utc,ended_at_utc")
    assert "None" not in csv_path.read_text(encoding="utf-8")


@pytest.mark.parametrize("format", ["jpg", "png"])
def test_manual_capture_real_encoding_and_metadata(repository, tmp_path, format):
    frame = color_frame()
    capture = CapturedFrame(frame.sequence, frame.captured_at, frame.image.copy())
    files = FileSystemCaptureStorage(tmp_path, tmp_path / "capturas con espacios")
    record = files.save_capture(capture, format)
    repository.insert("captures", record)
    path = resolve_capture_path(tmp_path, record["relative_path"])
    payload = path.read_bytes()
    assert payload.startswith(b"\xff\xd8") if format == "jpg" else payload.startswith(b"\x89PNG")
    image = cv2.imdecode(np.frombuffer(payload, np.uint8), cv2.IMREAD_COLOR)
    assert image.shape == frame.image.shape
    assert repository.query("captures", {}, 50, 0)[0]["created_at_utc"].endswith("Z")
    with pytest.raises(ValueError):
        resolve_capture_path(tmp_path, "../outside.png")
    with pytest.raises(ValueError):
        files.save_capture(capture, "../png")


def test_capture_write_failure_does_not_create_row(repository, tmp_path):
    blocked = tmp_path / "not_a_folder"
    blocked.write_text("blocked", encoding="utf-8")
    frame = color_frame()
    with pytest.raises(OSError):
        FileSystemCaptureStorage(tmp_path, blocked).save_capture(CapturedFrame(0, frame.captured_at, frame.image), "png")
    assert repository.query("captures", {}, 50, 0) == []


def test_locked_db_fails_without_commit_and_naive_time_rejected(repository):
    lock = sqlite3.connect(repository.path)
    try:
        lock.execute("BEGIN IMMEDIATE")
        with pytest.raises(sqlite3.OperationalError):
            repository.create_session(session_record())
    finally:
        lock.rollback()
        lock.close()
    assert repository.query("vision_sessions", {}, 50, 0) == []
    with pytest.raises(ValueError, match="UTC"):
        repository.create_session(dict(session_record(), started_at_utc="2026-10-06T12:00:00"))
