import asyncio
import json
import sqlite3
from pathlib import Path
from time import monotonic, sleep

import pytest
from PySide6.QtCore import QTimer
from websockets.asyncio.client import connect

from blanquita_vision.adapters.storage.sqlite_vision_repository import SQLiteVisionRepository
from blanquita_vision.domain.models.protocol import EmptyPayload, ProtocolEnvelope, message
from blanquita_vision.domain.models.vision_observation import VisionPipelineState
from blanquita_vision.presentation.main_window import MainWindow
from blanquita_vision.presentation.workers.storage_worker import QtStorageController
from tests.fixtures.vision_fakes import test_parameters as parameters
from tests.integration.test_camera_lifecycle import start_stream
from tests.unit.test_calibration_position_filter import calibration_points
from tests.unit.test_sqlite_and_captures import session_record


def query(storage, wait_until, category, filters=None):
    results = []
    storage.submit("query", dict(category=category, filters=filters or {}),
                   callback=lambda result, error: results.append((result, error)))
    wait_until(lambda: bool(results))
    assert results[0][1] is None, results[0][1]
    return results[0][0]


def test_session_local_lifecycle_metric_aggregation_and_no_auto_captures(operational_setup, wait_until):
    device, camera, runner, vision, calibration, operations = operational_setup()
    storage = operations.service.storage
    start_stream(camera, runner, wait_until)
    vision.configure(parameters(), 0.5)
    vision.start()
    wait_until(lambda: vision.last_result is not None)
    session = operations.service.session_id
    assert session is not None
    wait_until(lambda: vision.last_result.metrics.frames_processed >= 4)
    operations.service.metrics.started = monotonic() - 1.1
    operations.service.tick()
    vision.stop()
    wait_until(lambda: not vision.runner.active)
    sessions = query(storage, wait_until, "vision_sessions")
    assert len(sessions) == 1
    assert sessions[0]["start_source"] == "local_ui"
    assert sessions[0]["ended_at_utc"].endswith("Z")
    assert sessions[0]["end_reason"] == "local_stop"
    samples = query(storage, wait_until, "metric_samples")
    assert 1 <= len(samples) <= 2
    assert query(storage, wait_until, "detections")
    assert query(storage, wait_until, "captures") == []
    assert query(storage, wait_until, "vision_reports") == []


def test_mobile_commands_use_same_controller_and_are_idempotent(operational_setup, wait_until, qapp):
    device, camera, runner, vision, calibration, operations = operational_setup()
    start_stream(camera, runner, wait_until)
    vision.configure(parameters(), 0.5)
    server = operations.service.network.server
    async def run():
        async def pump():
            while True:
                qapp.processEvents()
                await asyncio.sleep(0.005)
        pumping = asyncio.create_task(pump())
        try:
            async with connect(f"ws://127.0.0.1:{server.health()['port']}/vision") as client:
                for _ in range(5):
                    ProtocolEnvelope.model_validate_json(await client.recv())
                assert vision.state is VisionPipelineState.STOPPED
                for _ in range(2):
                    await client.send(message("vision.start", EmptyPayload()).model_dump_json())
                deadline = monotonic() + 3
                while vision.last_result is None and monotonic() < deadline:
                    await asyncio.sleep(0.01)
                assert vision.state is VisionPipelineState.RUNNING
                active_session = operations.service.session_id
                report = None
                while report is None:
                    packet = ProtocolEnvelope.model_validate_json(await asyncio.wait_for(client.recv(), 3))
                    if packet.type == "vision.report":
                        report = packet
                assert report.payload.position.x is None
                assert report.payload.position.unit == "mm"
                await client.send(message("vision.stop", EmptyPayload()).model_dump_json())
                await client.send(message("vision.stop", EmptyPayload()).model_dump_json())
                deadline = monotonic() + 3
                while vision.runner.active and monotonic() < deadline:
                    await asyncio.sleep(0.01)
                assert vision.state is VisionPipelineState.STOPPED
                assert camera.runtime.state.value == "STREAMING"
        finally:
            pumping.cancel()
            await asyncio.gather(pumping, return_exceptions=True)
    asyncio.run(run())
    sessions = query(operations.service.storage, wait_until, "vision_sessions")
    assert len(sessions) == 1
    assert sessions[0]["start_source"] == "mobile"
    assert sessions[0]["end_reason"] == "mobile_stop"
    reports = query(operations.service.storage, wait_until, "vision_reports")
    assert reports
    assert all(row["session_id"] == sessions[0]["session_id"] for row in reports)


def test_calibration_persists_and_reloads_after_restart(operational_setup, wait_until, tmp_path):
    root = tmp_path / "persistent"
    device, camera, runner, vision, calibration, operations = operational_setup(root)
    start_stream(camera, runner, wait_until)
    candidate = calibration.compute(calibration_points(), "0", 160, 120)
    calibration.apply(candidate)
    rows = query(operations.service.storage, wait_until, "calibrations")
    assert rows[0]["unit"] == "mm"
    device2, camera2, runner2, vision2, calibration2, operations2 = operational_setup(root)
    start_stream(camera2, runner2, wait_until)
    wait_until(lambda: calibration2.active() is not None)
    assert calibration2.active().id == candidate.id
    calibration2.invalidate()
    invalid = query(operations2.service.storage, wait_until, "calibrations")
    assert invalid[0]["status"] == "INVALID"


def test_manual_capture_formats_settings_and_metadata(operational_setup, wait_until):
    device, camera, runner, vision, calibration, operations = operational_setup()
    storage = operations.service.storage
    start_stream(camera, runner, wait_until)
    for format in ("png", "jpg"):
        saved = []
        storage.submit("settings.save", {"settings": {"capture_format": format}}, critical=True,
                       callback=lambda result, error: saved.append((result, error)))
        wait_until(lambda: bool(saved))
        assert not saved[0][1]
        captured = []
        operations.service.capture(lambda result, error: captured.append((result, error)))
        wait_until(lambda: bool(captured))
        assert not captured[0][1]
        record = captured[0][0]
        assert record["format"] == format
        assert record["session_id"] is None
        assert Path(storage.data_root / record["relative_path"]).is_file()
    rows = query(storage, wait_until, "captures")
    assert len(rows) == 2
    assert all(row["x_mm"] is None for row in rows)


def test_storage_queue_is_bounded_and_ui_timer_runs(tmp_path, qapp, wait_until):
    class SlowRepository(SQLiteVisionRepository):
        def insert(self, table, record):
            sleep(0.08)
            super().insert(table, record)
    storage = QtStorageController(tmp_path, SlowRepository, capacity=4, ordinary_limit=2)
    ticks = []
    timer = QTimer()
    timer.setInterval(5)
    timer.timeout.connect(lambda: ticks.append(1))
    try:
        storage.start()
        wait_until(lambda: storage.health["state"] == "READY")
        timer.start()
        assert storage.submit("insert", {"table": "vision_sessions", "record": session_record("1")})
        assert storage.submit("insert", {"table": "vision_sessions", "record": session_record("2")})
        assert not storage.submit("insert", {"table": "vision_sessions", "record": session_record("3")})
        assert storage.submit("insert", {"table": "vision_sessions", "record": session_record("4")}, critical=True)
        assert storage.submit("insert", {"table": "vision_sessions", "record": session_record("5")}, critical=True)
        assert not storage.submit("insert", {"table": "vision_sessions", "record": session_record("6")}, critical=True)
        assert storage.health["queue_depth"] == 4
        wait_until(lambda: storage.health["queue_depth"] == 0)
        assert len(ticks) >= 10
        assert storage.health["rejected_jobs"] == 2
    finally:
        timer.stop()
        storage.shutdown()
        wait_until(lambda: not storage.active)


def test_db_locked_degrades_storage_without_global_crash(operational_setup, wait_until):
    device, camera, runner, vision, calibration, operations = operational_setup()
    storage = operations.service.storage
    # Aislar la inyección del bloqueo de las consultas periódicas de diagnóstico.
    operations.timer.stop()
    wait_until(lambda: storage.health["queue_depth"] == 0)
    lock = sqlite3.connect(storage.health["path"])
    result = []
    try:
        lock.execute("BEGIN IMMEDIATE")
        storage.submit("insert", {"table": "vision_sessions", "record": session_record()}, critical=True,
                       callback=lambda value, error: result.append(error))
        wait_until(lambda: bool(result), timeout=3)
        assert "locked" in result[0].lower()
        assert storage.health["state"] == "DEGRADED"
        assert operations.service.network.server.health()["state"] == "LISTENING"
    finally:
        lock.rollback()
        lock.close()


def test_unavailable_db_does_not_disable_local_perception(operational_setup, wait_until):
    class UnavailableRepository(SQLiteVisionRepository):
        def open(self):
            raise OSError("BD de prueba no disponible")
    device, camera, runner, vision, calibration, operations = operational_setup(repository_factory=UnavailableRepository,
                                                                              expect_storage="ERROR")
    start_stream(camera, runner, wait_until)
    vision.configure(parameters(), 0.5)
    vision.start()
    wait_until(lambda: vision.last_result is not None)
    assert operations.service.storage.health["state"] == "ERROR"
    assert vision.state is VisionPipelineState.RUNNING
    assert operations.service.network.server.health()["state"] == "LISTENING"


def test_reports_exports_diagnostics_and_shutdown(operational_setup, wait_until, tmp_path):
    device, camera, runner, vision, calibration, operations = operational_setup()
    window = MainWindow(camera, runner, vision=vision, calibration=calibration, operations=operations)
    window.show()
    try:
        start_stream(camera, runner, wait_until)
        vision.configure(parameters(), 0.5)
        vision.start()
        wait_until(lambda: vision.last_result is not None)
        vision.stop()
        wait_until(lambda: not vision.runner.active)
        browser = window.reports_screen.browser
        browser.load()
        wait_until(lambda: bool(browser.rows))
        assert browser.rows[0]["start_source"] == "local_ui"
        path = tmp_path / "export.json"
        browser.export_to(str(path), "json")
        wait_until(lambda: "Exportadas" in browser.message.text())
        assert json.loads(path.read_text(encoding="utf-8"))[0]["started_at_utc"].endswith("Z")
        window.diagnostics_screen.refresh()
        assert window.diagnostics_screen.tree.topLevelItemCount() == 6
        system = window.diagnostics_screen.tree.topLevelItem(5)
        assert any(system.child(index).text(1) == "No disponible" for index in range(system.childCount()))
        assert "Vision Server" in window.live.network_label.text()
        window.close()
        wait_until(lambda: not operations.active and not runner.active and not window.isVisible(), timeout=10)
    finally:
        window.close()


def test_capture_metadata_failure_retains_file_and_reports_failure(operational_setup, wait_until):
    class MetadataFailureRepository(SQLiteVisionRepository):
        def insert(self, table, record):
            if table == "captures":
                raise sqlite3.IntegrityError("metadata de prueba rechazada")
            super().insert(table, record)
    device, camera, runner, vision, calibration, operations = operational_setup(repository_factory=MetadataFailureRepository)
    start_stream(camera, runner, wait_until)
    result = []
    operations.service.capture(lambda value, error: result.append((value, error)))
    wait_until(lambda: bool(result))
    assert result[0][0] is None
    assert "archivo conservado" in result[0][1]
    storage = operations.service.storage
    assert len(list((storage.data_root / "captures").glob("*.jpg"))) == 1
    assert query(storage, wait_until, "captures") == []


def test_manual_capture_queue_has_two_image_limit(operational_setup, wait_until):
    device, camera, runner, vision, calibration, operations = operational_setup()
    start_stream(camera, runner, wait_until)
    replies = []
    for _ in range(3):
        operations.service.capture(lambda result, error: replies.append((result, error)))
    assert operations.service.storage.health["captures_pending"] == 2
    assert any(error for result, error in replies)
    wait_until(lambda: len(replies) == 3)
    assert sum(error is None for result, error in replies) == 2


def test_invalid_settings_are_rejected_without_replacing_current_values(operational_setup, wait_until):
    device, camera, runner, vision, calibration, operations = operational_setup()
    storage = operations.service.storage
    replies = []
    storage.submit("settings.save", {"settings": {"capture_format": "gif"}}, critical=True,
                   callback=lambda result, error: replies.append(error))
    wait_until(lambda: bool(replies))
    assert replies[0]
    assert storage.settings["capture_format"] == "jpg"


def test_session_reconfigure_inherits_mobile_origin(operational_setup, wait_until):
    device, camera, runner, vision, calibration, operations = operational_setup()
    start_stream(camera, runner, wait_until)
    vision.configure(parameters(), 0.5)
    vision.start(source="mobile")
    wait_until(lambda: vision.last_result is not None)
    first = operations.service.session_id
    vision.configure(parameters(), 0.6)
    wait_until(lambda: vision.last_result is not None and operations.service.session_id != first)
    sessions = query(operations.service.storage, wait_until, "vision_sessions")
    assert len(sessions) == 2
    assert all(row["start_source"] == "mobile" for row in sessions)


def test_late_autoload_does_not_override_manual_invalidation(operational_setup, wait_until):
    device, camera, runner, vision, calibration, operations = operational_setup()
    operations.timer.stop()
    start_stream(camera, runner, wait_until)
    candidate = calibration.compute(calibration_points(), "0", 160, 120)
    saved = []
    operations.service.storage.submit("calibration.save", {"calibration": candidate}, critical=True,
                                     callback=lambda value, error: saved.append(error))
    wait_until(lambda: bool(saved))
    operations.service._load_key = None
    operations.service._auto_load()
    calibration.invalidate()
    wait_until(lambda: operations.service.storage.health["queue_depth"] == 0)
    assert calibration.active() is None
