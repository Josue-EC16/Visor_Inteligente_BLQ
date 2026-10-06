import asyncio
import json
import logging
from collections import deque
from datetime import datetime, timezone
from http import HTTPStatus
from threading import Event, Lock
from time import perf_counter
from uuid import UUID

from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed

from ...domain.models.protocol import (
    CalibrationStatusPayload, CameraStatusPayload, ErrorPayload, HeartbeatPayload,
    HelloPayload, ReadyPayload, StatusPayload, message, parse_command, utc_text,
)

logger = logging.getLogger(__name__)


class WebSocketVisionServer:
    def __init__(self, host="0.0.0.0", port=8765, heartbeat_seconds=2.0, send_timeout=3.0) -> None:
        self.host, self.port = host, port
        self.heartbeat_seconds, self.send_timeout = heartbeat_seconds, send_timeout
        self._lock = Lock()
        self._stop_requested = Event()
        self._loop = None
        self._stop = None
        self._wake = None
        self._wake_pending = False
        self._client = None
        self._pending_report = None
        self._statuses = {}
        self._responses = deque()
        self._commands = deque()
        self._events = deque()
        self._command_count = 0
        self._snapshot = dict(ready=ReadyPayload(ready=False, cameraState="DISCONNECTED", pipelineState="STOPPED", calibrationStatus="UNCALIBRATED"),
                              status=StatusPayload(cameraState="DISCONNECTED", pipelineState="STOPPED", calibrationStatus="UNCALIBRATED"),
                              camera=CameraStatusPayload(state="DISCONNECTED"), calibration=CalibrationStatusPayload(status="UNCALIBRATED"))
        self._health = dict(state="STOPPED", host=host, port=port, path="/vision", client=False,
                            connected_since=None, last_rx=None, last_tx=None, last_heartbeat=None,
                            last_error=None, reports_produced=0, reports_sent=0, reports_dropped=0,
                            send_duration_ms=None, events_dropped=0, report_sending=False)

    def health(self) -> dict:
        with self._lock:
            return dict(self._health)

    def _set_health(self, **values) -> None:
        with self._lock:
            self._health.update(values)

    def update_snapshot(self, ready, status, camera, calibration) -> None:
        with self._lock:
            self._snapshot = dict(ready=ready, status=status, camera=camera, calibration=calibration)

    def _notify(self) -> None:
        with self._lock:
            if self._wake_pending or self._loop is None or self._wake is None:
                return
            self._wake_pending = True
            loop, wake = self._loop, self._wake
        try:
            loop.call_soon_threadsafe(wake.set)
        except RuntimeError:
            pass

    def publish_report(self, report, context=None) -> bool:
        with self._lock:
            if not self._health["client"]:
                return False
            self._health["reports_produced"] += 1
            if self._pending_report is not None:
                self._health["reports_dropped"] += 1
            self._pending_report = report, context or {}
        self._notify()
        return True

    def clear_pending_report(self) -> None:
        with self._lock:
            if self._pending_report is not None:
                self._health["reports_dropped"] += 1
            self._pending_report = None

    def publish_status(self, status) -> None:
        with self._lock:
            if not self._health["client"]:
                return
            self._statuses[status.type] = status
        self._notify()

    def publish_error(self, error) -> None:
        with self._lock:
            if not self._health["client"]:
                return
            if len(self._responses) >= 32:
                self._health["last_error"] = "Cola de respuestas saturada."
                self._health["events_dropped"] += 1
                logger.warning("network_response_queue_full")
                return
            self._responses.append(error)
        self._notify()

    def commands(self) -> list:
        with self._lock:
            commands = list(self._commands)
            self._commands.clear()
            return commands

    def complete_command(self, envelope, error=None) -> None:
        with self._lock:
            self._command_count = max(0, self._command_count - 1)
            status = self._snapshot["status"]
        if error:
            self.publish_error(message("vision.error", ErrorPayload(code="vision_precondition", message=str(error), recoverable=True,
                                                                   replyToMessageId=envelope.messageId)))
        else:
            self.publish_status(message("vision.status", status))

    def events(self) -> list:
        with self._lock:
            events = list(self._events)
            self._events.clear()
            return events

    def _event(self, kind: str, **data) -> None:
        with self._lock:
            if len(self._events) >= 256:
                self._health["events_dropped"] += 1
                logger.warning("network_event_queue_full kind=%s", kind)
                return
            self._events.append(dict(kind=kind, timestamp=utc_text(datetime.now(timezone.utc)), **data))

    def request_stop(self) -> None:
        self._stop_requested.set()
        with self._lock:
            loop, stop = self._loop, self._stop
        if loop is not None and stop is not None:
            try:
                loop.call_soon_threadsafe(stop.set)
            except RuntimeError:
                pass

    def process_request(self, connection, request):
        if request.path != "/vision":
            return connection.respond(HTTPStatus.NOT_FOUND, "Use /vision\n")
        return None

    async def run(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._stop, self._wake = asyncio.Event(), asyncio.Event()
        if self._stop_requested.is_set():
            self._set_health(state="STOPPED")
            return
        self._set_health(state="STARTING")
        try:
            async with serve(self._handler, self.host, self.port, process_request=self.process_request,
                             max_size=64 * 1024, max_queue=16, close_timeout=2, ping_interval=None) as server:
                actual_port = server.sockets[0].getsockname()[1]
                self._set_health(state="LISTENING", port=actual_port)
                self._event("network_server_listening")
                if self._stop_requested.is_set():
                    self._stop.set()
                await self._stop.wait()
                self._set_health(state="STOPPING")
        except Exception as exc:
            logger.error("network_server_error", exc_info=True)
            self._set_health(state="ERROR", last_error=str(exc))
            self._event("network_server_error", message=str(exc))
        finally:
            if self.health()["state"] != "ERROR":
                self._set_health(state="STOPPED", client=False)
            with self._lock:
                self._loop = self._stop = self._wake = None

    async def _write(self, connection, envelope, context=None) -> None:
        started = perf_counter()
        if envelope.type == "vision.report":
            self._set_health(report_sending=True)
        try:
            await asyncio.wait_for(connection.send(envelope.model_dump_json()), timeout=self.send_timeout)
        finally:
            if envelope.type == "vision.report":
                self._set_health(report_sending=False)
        now = utc_text(datetime.now(timezone.utc))
        self._set_health(last_tx=now)
        if envelope.type == "vision.heartbeat":
            self._set_health(last_heartbeat=now)
        if envelope.type == "vision.report":
            with self._lock:
                self._health["reports_sent"] += 1
                self._health["send_duration_ms"] = (perf_counter() - started) * 1000
            self._event("vision_report_sent", report=envelope, context=context or {})

    async def _sender(self, connection) -> None:
        while True:
            await self._wake.wait()
            with self._lock:
                context = None
                if self._responses:
                    envelope = self._responses.popleft()
                elif self._statuses:
                    key = next(iter(self._statuses))
                    envelope = self._statuses.pop(key)
                elif self._pending_report is not None:
                    envelope, context = self._pending_report
                    self._pending_report = None
                else:
                    envelope = None
                pending = bool(self._responses or self._statuses or self._pending_report)
                if not pending:
                    self._wake.clear()
                    self._wake_pending = False
            if envelope is not None:
                await self._write(connection, envelope, context)

    async def _heartbeat(self) -> None:
        while True:
            await asyncio.sleep(self.heartbeat_seconds)
            with self._lock:
                ready = self._snapshot["ready"].ready
            self.publish_status(message("vision.heartbeat", HeartbeatPayload(serverTime=datetime.now(timezone.utc), ready=ready)))

    async def _receiver(self, connection) -> None:
        async for text in connection:
            self._set_health(last_rx=utc_text(datetime.now(timezone.utc)))
            if not isinstance(text, str):
                self._event("protocol_message_invalid", message="Binary message rejected")
                await connection.close(1003, "Text JSON required")
                return
            fatal = False
            try:
                raw = json.loads(text)
                if isinstance(raw, dict):
                    fatal = ("protocol" in raw and raw["protocol"] != "blanquita-vision"
                             or "version" in raw and (type(raw["version"]) is not int or raw["version"] != 1))
                envelope = parse_command(text)
                if envelope.type == "vision.ping":
                    with self._lock:
                        ready = self._snapshot["ready"].ready
                    self.publish_error(message("vision.heartbeat", HeartbeatPayload(serverTime=datetime.now(timezone.utc),
                                                                                   ready=ready, replyToMessageId=envelope.messageId)))
                else:
                    with self._lock:
                        if self._command_count >= 32:
                            raise ValueError("Command queue full")
                        self._command_count += 1
                        self._commands.append(envelope)
            except (ValueError, TypeError):
                self._event("protocol_message_invalid", message="Invalid protocol message")
                self.publish_error(message("vision.error", ErrorPayload(code="protocol_incompatible" if fatal else "message_invalid",
                                                                        message="Invalid protocol message", recoverable=not fatal)))
                if fatal:
                    await connection.close(1008, "Protocol/version incompatible")
                    return

    async def _handler(self, connection) -> None:
        if self._client is not None:
            self._event("second_client_rejected")
            await connection.close(1008, "One Mobile client allowed")
            return
        self._client = connection
        self._set_health(state="CLIENT_CONNECTED", client=True, connected_since=utc_text(datetime.now(timezone.utc)))
        self._event("mobile_connected")
        tasks = []
        try:
            with self._lock:
                snapshot = dict(self._snapshot)
            for kind, payload in (("vision.hello", HelloPayload()), ("vision.ready", snapshot["ready"]),
                                  ("vision.status", snapshot["status"]), ("camera.status", snapshot["camera"]),
                                  ("calibration.status", snapshot["calibration"])):
                await self._write(connection, message(kind, payload))
            tasks = [asyncio.create_task(self._sender(connection)), asyncio.create_task(self._heartbeat()),
                     asyncio.create_task(self._receiver(connection))]
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                task.result()
        except ConnectionClosed:
            pass
        except Exception as exc:
            self._set_health(last_error=str(exc))
            self._event("network_client_error", message=str(exc))
            await connection.close(1011, "Connection operation failed")
        finally:
            for task in tasks:
                task.cancel()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            await connection.close()
            self._client = None
            self.clear_pending_report()
            with self._lock:
                self._statuses.clear()
                self._responses.clear()
                self._commands.clear()
                self._command_count = 0
                self._wake_pending = False
                self._wake.clear()
            self._set_health(state="STOPPING" if self._stop_requested.is_set() else "LISTENING",
                             client=False, connected_since=None)
            self._event("mobile_disconnected")
