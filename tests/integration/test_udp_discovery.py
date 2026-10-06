import asyncio
import socket
from time import monotonic

import pytest
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed

from blanquita_vision.adapters.network.udp_discovery_responder import IPV4_DATAGRAM_BUFFER_SIZE, UdpDiscoveryResponder
from blanquita_vision.adapters.network.websocket_vision_server import WebSocketVisionServer
from blanquita_vision.domain.models.discovery import DISCOVERY_REQUEST, DISCOVERY_RESPONSE, DiscoveryServiceState
from blanquita_vision.domain.models.protocol import EmptyPayload, ProtocolEnvelope, message
from tests.integration.test_websocket_protocol import start_server, welcome


async def wait_async(predicate, timeout=3):
    deadline = monotonic() + timeout
    while not predicate() and monotonic() < deadline:
        await asyncio.sleep(0.005)
    assert predicate(), "La condición de discovery no se cumplió."


async def start_discovery(snapshot=lambda: {"state": "LISTENING"}, host="127.0.0.1", port=0, **kwargs):
    responder = UdpDiscoveryResponder(snapshot, host, port, **kwargs)
    task = asyncio.create_task(responder.run())
    await wait_async(lambda: responder.snapshot().state in (DiscoveryServiceState.LISTENING, DiscoveryServiceState.ERROR))
    return responder, task


async def query_udp(responder, data=DISCOVERY_REQUEST, timeout=1):
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        client.setblocking(False)
        client.bind(("127.0.0.1", 0))
        source_port = client.getsockname()[1]
        loop = asyncio.get_running_loop()
        await loop.sock_sendto(client, data, ("127.0.0.1", responder.snapshot().udp_port))
        response, origin = await asyncio.wait_for(loop.sock_recvfrom(client, IPV4_DATAGRAM_BUFFER_SIZE), timeout)
        return response, origin, source_port
    finally:
        client.close()


def test_tc_064_065_066_literal_response_to_ephemeral_origin():
    async def run():
        responder, task = await start_discovery()
        try:
            response, origin, port = await query_udp(responder)
            assert port != responder.snapshot().udp_port
            assert response == b"BLANQUITA_VISION_HERE:8765"
            assert origin == ("127.0.0.1", responder.snapshot().udp_port)
            assert responder.snapshot().valid_requests_count == 1
            assert responder.snapshot().responses_sent_count == 1
            assert not response.endswith(b"\n")
        finally:
            responder.request_stop()
            await task
    asyncio.run(run())


@pytest.mark.parametrize("payload", [
    b"", b"OTHER", DISCOVERY_REQUEST.lower(), b"\xef\xbb\xbf" + DISCOVERY_REQUEST,
    b" " + DISCOVERY_REQUEST, DISCOVERY_REQUEST + b"\n", DISCOVERY_REQUEST + b"\r\n",
    DISCOVERY_REQUEST + b"\x00", DISCOVERY_REQUEST + b"extra", b"\xff\xfe",
    DISCOVERY_REQUEST + b"x" * 60000,
    b'{"type":"vision.start","payload":{}}', b'{"type":"vision.stop"}',
    b'{"type":"vision.ping"}', b'{"command":"d"}',
], ids=["empty", "other", "lowercase", "bom", "space", "newline", "crlf", "nul", "suffix", "non_utf8",
        "oversized_valid_prefix", "vision_start", "vision_stop", "vision_ping", "physical_command"])
def test_tc_067_075_invalid_operational_or_oversized_datagrams_ignored(payload):
    async def run():
        responder, task = await start_discovery()
        try:
            with pytest.raises(asyncio.TimeoutError):
                await query_udp(responder, payload, timeout=0.1)
            status = responder.snapshot()
            assert status.invalid_requests_count == 1
            assert status.valid_requests_count == status.responses_sent_count == 0
            assert status.state is DiscoveryServiceState.LISTENING
            assert IPV4_DATAGRAM_BUFFER_SIZE >= 65507
        finally:
            responder.request_stop()
            await task
    asyncio.run(run())


@pytest.mark.parametrize("state", ["STOPPED", "STARTING", "STOPPING", "ERROR"])
def test_tc_071_no_advertisement_until_websocket_available(state):
    async def run():
        health = {"state": state}
        responder, task = await start_discovery(lambda: dict(health))
        try:
            port = responder.snapshot().udp_port
            assert not responder.snapshot().websocket_advertisable
            with pytest.raises(asyncio.TimeoutError):
                await query_udp(responder, timeout=0.1)
            assert responder.snapshot().suppressed_requests_count == 1
            health["state"] = "LISTENING"
            assert (await query_udp(responder))[0] == DISCOVERY_RESPONSE
            assert responder.snapshot().udp_port == port
        finally:
            responder.request_stop()
            await task
    asyncio.run(run())


def test_tc_070_isolated_send_failure_and_next_request_recovers():
    async def run():
        responder, task = await start_discovery()
        native_send = responder._send
        failed = False
        async def fail_once(sock, target):
            nonlocal failed
            if not failed:
                failed = True
                raise OSError("fallo de envío de prueba")
            await native_send(sock, target)
        responder._send = fail_once
        try:
            with pytest.raises(asyncio.TimeoutError):
                await query_udp(responder, timeout=0.1)
            assert responder.snapshot().send_errors_count == 1
            assert responder.snapshot().responses_sent_count == 0
            assert responder.snapshot().state is DiscoveryServiceState.LISTENING
            assert (await query_udp(responder))[0] == DISCOVERY_RESPONSE
            assert responder.snapshot().responses_sent_count == 1
        finally:
            responder.request_stop()
            await task
    asyncio.run(run())


def test_windows_remote_udp_reset_does_not_kill_responder():
    async def run():
        responder = UdpDiscoveryResponder(lambda: {"state": "LISTENING"}, "127.0.0.1", 0)
        original = responder._receive
        failed = False
        async def reset_once(sock):
            nonlocal failed
            if not failed:
                failed = True
                raise ConnectionResetError("ICMP del peer de prueba")
            return await original(sock)
        responder._receive = reset_once
        task = asyncio.create_task(responder.run())
        try:
            await wait_async(lambda: responder.snapshot().send_errors_count == 1)
            assert responder.snapshot().state is DiscoveryServiceState.LISTENING
            assert (await query_udp(responder))[0] == DISCOVERY_RESPONSE
        finally:
            responder.request_stop()
            await task
    asyncio.run(run())


def test_tc_068_udp_bind_error_does_not_prevent_websocket_start():
    async def run():
        busy = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        busy.bind(("127.0.0.1", 0))
        server = WebSocketVisionServer("127.0.0.1", 0)
        responder, udp_task = await start_discovery(server.health, port=busy.getsockname()[1])
        ws_task = asyncio.create_task(server.run())
        try:
            assert responder.snapshot().state is DiscoveryServiceState.ERROR
            assert responder.snapshot().last_error
            await wait_async(lambda: server.health()["state"] == "LISTENING")
            async with connect(f"ws://127.0.0.1:{server.health()['port']}/vision") as client:
                await welcome(client)
                await client.send(message("vision.ping", EmptyPayload()).model_dump_json())
                assert ProtocolEnvelope.model_validate_json(await client.recv()).type == "vision.heartbeat"
        finally:
            responder.request_stop()
            server.request_stop()
            await asyncio.gather(udp_task, ws_task)
            busy.close()
    asyncio.run(run())


def test_tc_069_runtime_receive_error_keeps_websocket_client_and_heartbeat():
    async def run():
        server, ws_task, uri = await start_server()
        responder, udp_task = await start_discovery(server.health)
        try:
            async with connect(uri) as client:
                await welcome(client)
                async def failing_receive(sock):
                    raise OSError("fallo de recepción de prueba")
                responder._receive = failing_receive
                await query_udp(responder)
                await wait_async(lambda: responder.snapshot().state is DiscoveryServiceState.ERROR)
                assert server.health()["state"] == "CLIENT_CONNECTED"
                ping = message("vision.ping", EmptyPayload())
                await client.send(ping.model_dump_json())
                reply = ProtocolEnvelope.model_validate_json(await client.recv())
                assert reply.payload.replyToMessageId == ping.messageId
                periodic = ProtocolEnvelope.model_validate_json(await asyncio.wait_for(client.recv(), 3))
                assert periodic.type == "vision.heartbeat"
        finally:
            responder.request_stop()
            server.request_stop()
            await asyncio.gather(udp_task, ws_task)
    asyncio.run(run())


def test_tc_073_074_076_queries_do_not_reserve_client_and_udp_stop_is_independent():
    async def run():
        server, ws_task, uri = await start_server()
        responder, udp_task = await start_discovery(server.health)
        try:
            assert (await query_udp(responder))[0] == DISCOVERY_RESPONSE
            assert not server.health()["client"]
            async with connect(uri) as first:
                await welcome(first)
                for _ in range(3):
                    assert (await query_udp(responder))[0] == DISCOVERY_RESPONSE
                async with connect(uri) as second:
                    with pytest.raises(ConnectionClosed):
                        await second.recv()
                    assert second.close_code == 1008
                assert responder.snapshot().valid_requests_count == 4
                port = responder.snapshot().udp_port
                responder.request_stop()
                await asyncio.wait_for(udp_task, 2)
                assert responder.snapshot().state is DiscoveryServiceState.STOPPED
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
                    probe.bind(("127.0.0.1", port))
                await first.send(message("vision.ping", EmptyPayload()).model_dump_json())
                assert ProtocolEnvelope.model_validate_json(await first.recv()).type == "vision.heartbeat"
        finally:
            responder.request_stop()
            server.request_stop()
            await asyncio.gather(udp_task, ws_task)
    asyncio.run(run())


def test_stop_before_udp_run_does_not_bind_or_leave_worker():
    async def run():
        responder = UdpDiscoveryResponder(lambda: {"state": "LISTENING"}, "127.0.0.1", 0)
        responder.request_stop()
        await responder.run()
        assert responder.snapshot().state is DiscoveryServiceState.STOPPED
        assert responder.snapshot().udp_port == 0
    asyncio.run(run())


def test_tc_078_fixed_contract_discovery_then_websocket():
    async def run():
        server = WebSocketVisionServer("127.0.0.1", 8765)
        ws_task = asyncio.create_task(server.run())
        await wait_async(lambda: server.health()["state"] in ("LISTENING", "ERROR"))
        if server.health()["state"] == "ERROR":
            await ws_task
            pytest.skip("TCP 8765 está ocupado/no disponible para el test del endpoint fijo.")
        responder, udp_task = await start_discovery(server.health, host="0.0.0.0", port=4211)
        try:
            if responder.snapshot().state is DiscoveryServiceState.ERROR:
                pytest.skip("UDP 4211 está ocupado/no disponible para el test del endpoint fijo.")
            response, origin, _ = await query_udp(responder)
            assert origin[1] == 4211
            host = origin[0]
            port = int(response.decode("utf-8").split(":")[1])
            assert port == 8765
            async with connect(f"ws://{host}:{port}/vision") as client:
                await welcome(client)
                assert server.health()["client"]
        finally:
            responder.request_stop()
            server.request_stop()
            await asyncio.gather(udp_task, ws_task)
    asyncio.run(run())
