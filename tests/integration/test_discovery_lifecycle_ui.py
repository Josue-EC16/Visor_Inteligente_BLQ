import asyncio
import socket
from threading import get_ident

from PySide6.QtCore import QTimer

from blanquita_vision.domain.models.discovery import DISCOVERY_REQUEST, DISCOVERY_RESPONSE, DiscoveryServiceState
from blanquita_vision.presentation.main_window import MainWindow
from tests.integration.test_udp_discovery import query_udp
from tests.integration.test_camera_lifecycle import start_stream
from tests.fixtures.vision_fakes import test_parameters as parameters
from tests.integration.test_storage_operations_ui import query


def test_tc_072_077_discovery_without_camera_and_nested_diagnostics(operational_setup, wait_until):
    device, camera, runner, vision, calibration, operations = operational_setup(with_discovery=True)
    service, discovery = operations.service, operations.service.discovery
    window = MainWindow(camera, runner, vision=vision, calibration=calibration, operations=operations)
    responder = discovery.responder
    threads = []
    native_send = responder._send
    async def recorded_send(sock, target):
        threads.append(get_ident())
        await native_send(sock, target)
    responder._send = recorded_send
    try:
        assert camera.runtime.state.value == "DISCONNECTED"
        assert vision.state.value == "STOPPED"
        assert not service.ready()
        response, origin, client_port = asyncio.run(query_udp(responder))
        assert response == DISCOVERY_RESPONSE
        assert threads and all(thread != get_ident() for thread in threads)
        assert not service.network.server.health()["client"]
        assert service.session_id is None
        assert device.open_calls == []
        window.diagnostics_screen.refresh()
        network = window.diagnostics_screen.tree.topLevelItem(2)
        assert any(network.child(index).text(0) == "UDP DISCOVERY" for index in range(network.childCount()))
        assert query(service.storage, wait_until, "vision_sessions") == []
        window.close()
        wait_until(lambda: not operations.active)
        assert discovery.snapshot().state is DiscoveryServiceState.STOPPED
    finally:
        window.close()


def test_discovery_bind_failure_preserves_camera_vision_storage_and_ws(operational_setup, wait_until):
    def failing_socket(*args):
        raise OSError("bind de prueba no disponible")
    device, camera, runner, vision, calibration, operations = operational_setup(
        with_discovery=True, discovery_socket_factory=failing_socket,
    )
    service = operations.service
    wait_until(lambda: not service.discovery.active)
    assert service.discovery.snapshot().state is DiscoveryServiceState.ERROR
    start_stream(camera, runner, wait_until)
    vision.configure(parameters(), 0.5)
    vision.start()
    wait_until(lambda: vision.last_result is not None)
    assert service.storage.health["state"] == "READY"
    assert service.network.server.health()["state"] == "LISTENING"
    assert device.is_open


def test_tc_077_udp_traffic_does_not_block_ui_or_start_perception(operational_setup, wait_until):
    device, camera, runner, vision, calibration, operations = operational_setup(with_discovery=True)
    discovery = operations.service.discovery
    ticks = []
    timer = QTimer()
    timer.setInterval(5)
    timer.timeout.connect(lambda: ticks.append(1))
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    timer.start()
    try:
        for _ in range(100):
            client.sendto(b"invalid", ("127.0.0.1", discovery.snapshot().udp_port))
        client.sendto(DISCOVERY_REQUEST, ("127.0.0.1", discovery.snapshot().udp_port))
        wait_until(lambda: discovery.snapshot().valid_requests_count >= 1 and len(ticks) >= 3)
        assert discovery.snapshot().responses_sent_count >= 1
        assert vision.state.value == "STOPPED"
        assert camera.runtime.state.value == "DISCONNECTED"
        assert operations.service.network.server.health()["state"] == "LISTENING"
    finally:
        client.close()
        timer.stop()
