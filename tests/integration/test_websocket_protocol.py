import asyncio
import json
from datetime import datetime, timezone
from time import monotonic

import pytest
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed, InvalidStatus

from blanquita_vision.adapters.network.websocket_vision_server import WebSocketVisionServer
from blanquita_vision.domain.models.protocol import EmptyPayload, ProtocolEnvelope, message
from blanquita_vision.application.report_mapper import report_from_observation
from tests.fixtures.vision_fakes import color_frame
from tests.unit.test_vision_pipeline import pipeline


async def start_server(**kwargs):
    server = WebSocketVisionServer(host="127.0.0.1", port=0, **kwargs)
    task = asyncio.create_task(server.run())
    deadline = monotonic() + 3
    while server.health()["state"] != "LISTENING" and monotonic() < deadline:
        await asyncio.sleep(0.005)
    assert server.health()["state"] == "LISTENING"
    return server, task, f"ws://127.0.0.1:{server.health()['port']}/vision"


async def welcome(client):
    messages = [ProtocolEnvelope.model_validate_json(await asyncio.wait_for(client.recv(), 3)) for _ in range(5)]
    assert [packet.type for packet in messages] == ["vision.hello", "vision.ready", "vision.status", "camera.status", "calibration.status"]


def test_hello_ready_path_and_client_exclusivity():
    async def run():
        server, task, uri = await start_server()
        try:
            with pytest.raises(InvalidStatus) as error:
                async with connect(uri.replace("/vision", "/wrong")):
                    pass
            assert error.value.response.status_code == 404
            async with connect(uri) as first:
                await welcome(first)
                async with connect(uri) as second:
                    with pytest.raises(ConnectionClosed):
                        await second.recv()
                    assert second.close_code == 1008
                await first.send(message("vision.ping", EmptyPayload()).model_dump_json())
                heartbeat = ProtocolEnvelope.model_validate_json(await first.recv())
                assert heartbeat.type == "vision.heartbeat"
                assert server.health()["client"]
            await asyncio.sleep(0.03)
            assert server.health()["state"] == "LISTENING"
        finally:
            server.request_stop()
            await task
    asyncio.run(run())


def test_ping_correlation_and_real_heartbeat_cadence():
    async def run():
        server, task, uri = await start_server()
        try:
            async with connect(uri) as client:
                await welcome(client)
                ping = message("vision.ping", EmptyPayload())
                await client.send(ping.model_dump_json())
                reply = ProtocolEnvelope.model_validate_json(await client.recv())
                assert reply.payload.replyToMessageId == ping.messageId
                assert reply.payload.serverTime.tzinfo is not None
                started = monotonic()
                periodic = ProtocolEnvelope.model_validate_json(await asyncio.wait_for(client.recv(), 3))
                assert periodic.type == "vision.heartbeat"
                assert 1.5 < monotonic() - started < 3
                assert periodic.payload.replyToMessageId is None
        finally:
            server.request_stop()
            await task
    asyncio.run(run())


@pytest.mark.parametrize("content,fatal,code", [
    ("{broken", False, None), ('{"command":"d"}', False, None),
    ("incompatible", True, 1008), (b"binary", True, 1003), ("oversized", True, 1009),
])
def test_invalid_messages_never_dispatch_commands(content, fatal, code):
    async def run():
        server, task, uri = await start_server()
        try:
            async with connect(uri) as client:
                await welcome(client)
                data = content
                if content == "incompatible":
                    packet = json.loads(message("vision.start", EmptyPayload()).model_dump_json())
                    packet["version"] = 2
                    data = json.dumps(packet)
                elif content == "oversized":
                    data = "x" * (65 * 1024)
                await client.send(data)
                if fatal:
                    try:
                        while True:
                            await asyncio.wait_for(client.recv(), 3)
                    except ConnectionClosed:
                        assert client.close_code == code
                else:
                    reply = ProtocolEnvelope.model_validate_json(await client.recv())
                    assert reply.type == "vision.error"
                    await client.send(message("vision.ping", EmptyPayload()).model_dump_json())
                    assert ProtocolEnvelope.model_validate_json(await client.recv()).type == "vision.heartbeat"
                assert server.commands() == []
        finally:
            server.request_stop()
            await task
    asyncio.run(run())


def test_latest_only_slow_sender_keeps_one_pending_and_emits_only_sent():
    async def run():
        server = WebSocketVisionServer()
        server._loop = asyncio.get_running_loop()
        server._wake = asyncio.Event()
        server._set_health(client=True)
        entered, release = asyncio.Event(), asyncio.Event()
        wires = []
        class SlowConnection:
            async def send(self, text):
                if not wires:
                    entered.set()
                    await release.wait()
                wires.append(json.loads(text))
        sender = asyncio.create_task(server._sender(SlowConnection()))
        try:
            reports = [report_from_observation(pipeline().process(color_frame(i)).observation) for i in range(3)]
            server.publish_report(reports[0], {"session_id": "original"})
            await entered.wait()
            server.publish_report(reports[1])
            server.publish_report(reports[2])
            assert server._pending_report[0].payload.frameSequence == 2
            assert server.health()["reports_dropped"] == 1
            release.set()
            deadline = monotonic() + 2
            while len(wires) < 2 and monotonic() < deadline:
                await asyncio.sleep(0.01)
            assert [wire["payload"]["frameSequence"] for wire in wires] == [0, 2]
            events = server.events()
            assert [event["report"].payload.frameSequence for event in events] == [0, 2]
            assert events[0]["context"]["session_id"] == "original"
        finally:
            sender.cancel()
            await asyncio.gather(sender, return_exceptions=True)
    asyncio.run(run())
