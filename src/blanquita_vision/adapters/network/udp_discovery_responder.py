import asyncio
import logging
import socket
from dataclasses import replace
from threading import Event, Lock
from typing import Callable

from ...domain.models.discovery import (
    DISCOVERY_REQUEST, DISCOVERY_RESPONSE, DiscoveryServiceState, DiscoveryStatus,
)

logger = logging.getLogger(__name__)

# Capacidad para cualquier datagrama IPv4: nunca comparar un prefijo truncado.
IPV4_DATAGRAM_BUFFER_SIZE = 65535


class UdpDiscoveryResponder:
    """Socket propio, sin publicar datos operativos ni controlar WebSocket."""

    def __init__(self, websocket_snapshot: Callable[[], dict], host: str = "0.0.0.0",
                 port: int = 4211, socket_factory: Callable = socket.socket) -> None:
        self._websocket_snapshot = websocket_snapshot
        self._host, self._port = host, port
        self._socket_factory = socket_factory
        self._lock = Lock()
        self._status = DiscoveryStatus(DiscoveryServiceState.STOPPED, host, port)
        self._stop_requested = Event()
        self._loop = None
        self._stop_event = None

    def _update(self, **changes) -> None:
        with self._lock:
            self._status = replace(self._status, **changes)

    def _increment(self, name: str) -> None:
        with self._lock:
            self._status = replace(self._status, **{name: getattr(self._status, name) + 1})

    def _websocket_available(self) -> bool:
        return self._websocket_snapshot().get("state") in ("LISTENING", "CLIENT_CONNECTED")

    def snapshot(self) -> DiscoveryStatus:
        with self._lock:
            status = self._status
        eligible = status.state is DiscoveryServiceState.LISTENING and not self._stop_requested.is_set()
        if eligible:
            try:
                eligible = self._websocket_available()
            except Exception:
                # El fallo de consulta lo tratará el worker al atender una solicitud.
                eligible = False
        return replace(status, websocket_advertisable=eligible)

    def request_stop(self) -> None:
        self._stop_requested.set()
        with self._lock:
            loop, stop = self._loop, self._stop_event
            state = self._status.state
        if loop is not None and stop is not None:
            try:
                loop.call_soon_threadsafe(stop.set)
            except RuntimeError:
                # El loop ya terminó: cancelación idempotente.
                pass
        elif state is DiscoveryServiceState.ERROR:
            self._update(state=DiscoveryServiceState.STOPPED)

    async def _receive(self, udp_socket) -> tuple[bytes, tuple]:
        return await asyncio.get_running_loop().sock_recvfrom(udp_socket, IPV4_DATAGRAM_BUFFER_SIZE)

    async def _send(self, udp_socket, destination: tuple) -> None:
        written = await asyncio.get_running_loop().sock_sendto(udp_socket, DISCOVERY_RESPONSE, destination)
        if written != len(DISCOVERY_RESPONSE):
            raise OSError("Envío UDP incompleto.")

    async def _listen(self, udp_socket) -> None:
        while not self._stop_requested.is_set():
            try:
                data, source = await self._receive(udp_socket)
            except ConnectionResetError as exc:
                # Windows puede entregar aquí un ICMP de un peer UDP ya cerrado.
                # El socket local sigue utilizable; no reiniciar WS ni reenviar.
                self._increment("send_errors_count")
                self._update(last_error=f"Error UDP del destino remoto: {exc}")
                logger.warning("discovery_send_failed remote_peer_reset")
                continue
            if self._stop_requested.is_set():
                return
            if data != DISCOVERY_REQUEST:
                self._increment("invalid_requests_count")
                continue
            self._increment("valid_requests_count")
            if not self._websocket_available():
                self._increment("suppressed_requests_count")
                continue
            if self._stop_requested.is_set():
                return
            try:
                await self._send(udp_socket, source)
            except OSError as exc:
                self._increment("send_errors_count")
                self._update(last_error=f"No se pudo enviar la respuesta UDP: {exc}")
                logger.warning("discovery_send_failed", exc_info=True)
                continue
            self._increment("responses_sent_count")

    async def run(self) -> None:
        udp_socket = None
        tasks = []
        failed = False
        listening = False
        loop = asyncio.get_running_loop()
        stop = asyncio.Event()
        with self._lock:
            self._loop, self._stop_event = loop, stop
        try:
            if self._stop_requested.is_set():
                return
            self._update(state=DiscoveryServiceState.STARTING)
            logger.info("discovery_starting bind=%s:%s", self._host, self._port)
            udp_socket = self._socket_factory(socket.AF_INET, socket.SOCK_DGRAM)
            if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            udp_socket.setblocking(False)
            udp_socket.bind((self._host, self._port))
            actual_port = udp_socket.getsockname()[1]
            self._update(state=DiscoveryServiceState.LISTENING, udp_port=actual_port)
            listening = True
            logger.info("discovery_listening bind=%s:%s", self._host, actual_port)
            tasks = [asyncio.create_task(self._listen(udp_socket)), asyncio.create_task(stop.wait())]
            if self._stop_requested.is_set():
                stop.set()
            done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                task.result()
        except Exception as exc:
            failed = True
            self._update(state=DiscoveryServiceState.ERROR,
                         last_error=f"Error {'de recepción/socket' if listening else 'al iniciar'} UDP Discovery: {exc}")
            logger.error("discovery_receive_failed" if listening else "discovery_bind_failed", exc_info=True)
        finally:
            if not failed:
                self._update(state=DiscoveryServiceState.STOPPING)
                logger.info("discovery_stopping")
            for task in tasks:
                task.cancel()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            if udp_socket is not None:
                try:
                    udp_socket.close()
                except OSError as exc:
                    failed = True
                    self._update(state=DiscoveryServiceState.ERROR, last_error=f"Error al liberar UDP Discovery: {exc}")
                    logger.error("discovery_close_failed", exc_info=True)
            with self._lock:
                self._loop = self._stop_event = None
            if not failed or self._stop_requested.is_set():
                self._update(state=DiscoveryServiceState.STOPPED)
                logger.info("discovery_stopped")
