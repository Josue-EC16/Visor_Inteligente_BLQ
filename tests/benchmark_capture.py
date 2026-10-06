"""TC-00-023: medición explícita con cámara real, sin persistencia."""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic, process_time

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from blanquita_vision.adapters.camera.opencv_camera import OpenCvCamera
from blanquita_vision.application.camera_controller import CameraController
from blanquita_vision.application.latest_frame_store import LatestFrameStore
from blanquita_vision.domain.models.camera_device import CameraDevice
from blanquita_vision.domain.models.camera_state import CameraState
from blanquita_vision.infrastructure.logging import configure_logging
from blanquita_vision.presentation.main_window import MainWindow
from blanquita_vision.presentation.theme import THEME
from blanquita_vision.presentation.workers.camera_worker import QtCameraRunner


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark de captura con hardware real")
    parser.add_argument("--camera-index", type=int, required=True)
    parser.add_argument("--seconds", type=float, required=True)
    parser.add_argument("--backend", default="AUTO")
    args = parser.parse_args()
    if args.camera_index < 0 or not 0 < args.seconds < float("inf"):
        parser.error("Índice no negativo y duración finita positiva requeridos.")
    configure_logging()
    app = QApplication([sys.argv[0]])
    app.setStyleSheet(THEME)
    store = LatestFrameStore()
    runner = QtCameraRunner(
        lambda cancellation: OpenCvCamera(backend=args.backend,
                                           cancellation=cancellation), store,
    )
    controller = CameraController(runner, store, args.backend)
    window = MainWindow(controller, runner)
    controller.devices = [CameraDevice(str(args.camera_index), args.camera_index,
                                       f"Cámara {args.camera_index}")]
    controller.select(str(args.camera_index))
    started = None
    cpu_started = None
    frame_count = 0
    age_total = 0.0
    max_age = 0.0
    max_dispatch_gap = 0.0
    previous_dispatch = None
    captured_properties = None
    had_error = False
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(window.close)

    def state_changed(runtime):
        nonlocal started, cpu_started, captured_properties, had_error
        if runtime.state is CameraState.STREAMING:
            captured_properties = runtime.properties
            if started is None:
                started, cpu_started = monotonic(), process_time()
                timer.start(max(1, int(args.seconds * 1000)))
        elif runtime.state is CameraState.ERROR:
            had_error = True
            window.close()

    def rendered(frame):
        nonlocal frame_count, age_total, max_age, previous_dispatch, max_dispatch_gap
        now = monotonic()
        age = (datetime.now(timezone.utc) - frame.captured_at).total_seconds() * 1000
        frame_count += 1
        age_total += age
        max_age = max(max_age, age)
        if previous_dispatch is not None:
            max_dispatch_gap = max(max_dispatch_gap, (now - previous_dispatch) * 1000)
        previous_dispatch = now

    controller.on_state.append(state_changed)
    controller.on_frame.append(rendered)
    window.showMaximized()
    controller.connect()
    app.exec()
    elapsed = monotonic() - started if started is not None else None
    cpu_seconds = process_time() - cpu_started if cpu_started is not None else None
    metrics = store.metrics()
    properties = captured_properties
    print(json.dumps({
        "status": "benchmark_completed" if not had_error else "benchmark_error",
        "duration_seconds_including_shutdown": elapsed,
        "frames_captured": metrics.frames_captured,
        "invalid_frames": metrics.invalid_frames,
        "stale_frames_replaced": metrics.stale_frames_replaced,
        "reconnect_attempts": metrics.reconnect_attempts,
        "measured_capture_fps": metrics.measured_fps,
        "reported_fps": properties.reported_fps if properties else None,
        "resolution": [properties.width, properties.height] if properties else None,
        "backend": properties.backend_name if properties else None,
        "process_cpu_seconds": cpu_seconds,
        "approx_cpu_percent_one_core": 100 * cpu_seconds / elapsed if elapsed else None,
        "frames_delivered_to_ui": frame_count,
        "mean_frame_to_render_call_ms": age_total / frame_count if frame_count else None,
        "max_frame_to_render_call_ms": max_age if frame_count else None,
        "max_ui_frame_dispatch_gap_ms": max_dispatch_gap if frame_count > 1 else None,
    }, indent=2))
    return 1 if had_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
