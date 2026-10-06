"""TC-02-061: productor sintético y cliente loopback, sin interoperabilidad Mobile certificada."""
import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from websockets.asyncio.client import connect
from blanquita_vision.adapters.network.websocket_vision_server import WebSocketVisionServer
from blanquita_vision.domain.models.protocol import PositionPayload, ReportPayload, message


async def benchmark(reports: int, delay: float) -> dict:
    server = WebSocketVisionServer("127.0.0.1", 0)
    task = asyncio.create_task(server.run())
    while server.health()["state"] not in ("LISTENING", "ERROR"):
        await asyncio.sleep(0.005)
    started = perf_counter()
    received = 0
    try:
        if server.health()["state"] == "ERROR":
            raise RuntimeError(server.health()["last_error"])
        async with connect(f"ws://127.0.0.1:{server.health()['port']}/vision") as client:
            for _ in range(5):
                await client.recv()
            done = asyncio.Event()
            async def produce():
                for sequence in range(reports):
                    payload = ReportPayload(detected=False, position=PositionPayload(), confidence=0.0,
                                            calibrationStatus="UNCALIBRATED", trackingState="INACTIVE",
                                            frameSequence=sequence, observationTimestamp=datetime.now(timezone.utc))
                    server.publish_report(message("vision.report", payload))
                    await asyncio.sleep(0)
                done.set()
            producer = asyncio.create_task(produce())
            try:
                while True:
                    health = server.health()
                    if done.is_set() and received >= health["reports_sent"] and server._pending_report is None and not health["report_sending"]:
                        await asyncio.sleep(0.01)
                        if received >= server.health()["reports_sent"] and server._pending_report is None and not server.health()["report_sending"]:
                            break
                    packet = json.loads(await asyncio.wait_for(client.recv(), 5))
                    if packet["type"] == "vision.report":
                        received += 1
                        server.events()
                        if delay:
                            await asyncio.sleep(delay)
                await producer
            finally:
                producer.cancel()
                await asyncio.gather(producer, return_exceptions=True)
        health = server.health()
        return dict(status="completed", source="synthetic_loopback", requested_reports=reports,
                    produced=health["reports_produced"], sent=health["reports_sent"], received=received,
                    dropped_stale=health["reports_dropped"], last_send_duration_ms=health["send_duration_ms"],
                    elapsed_seconds=perf_counter() - started, rtt_ms=None)
    finally:
        server.request_stop()
        await task


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark sintético WebSocket")
    parser.add_argument("--reports", type=int, required=True)
    parser.add_argument("--client-delay", type=float, default=0)
    args = parser.parse_args()
    if args.reports < 1 or not 0 <= args.client_delay < float("inf"):
        parser.error("Cantidad positiva y demora finita no negativa requeridas.")
    print(json.dumps(asyncio.run(benchmark(args.reports, args.client_delay)), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
