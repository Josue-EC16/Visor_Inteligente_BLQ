import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run_script(script):
    env = os.environ.copy()
    env["QT_QPA_PLATFORM"] = "offscreen"
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=ROOT, env=env,
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_main_bootstrap_opens_and_closes_without_camera():
    run_script("""
import sys
import tempfile
sys.path.insert(0, 'src')
from PySide6.QtCore import QTimer
import blanquita_vision.main as entry
original = entry.MainWindow
class SmokeWindow(original):
    def showMaximized(self):
        super().showMaximized()
        assert not self.runner.active
        QTimer.singleShot(50, self.close)
entry.MainWindow = SmokeWindow
with tempfile.TemporaryDirectory() as data:
    raise SystemExit(entry.main(['--data-dir', data]))
""")


def test_benchmark_smoke_with_fake_does_not_claim_physical_validation():
    output = run_script("""
import sys
sys.path.insert(0, 'src')
from tests.fixtures.fake_camera import FakeCamera
from tests import benchmark_capture
benchmark_capture.OpenCvCamera = lambda **kwargs: FakeCamera(cancellation=kwargs.get('cancellation'))
sys.argv = ['benchmark', '--camera-index', '0', '--seconds', '0.1']
raise SystemExit(benchmark_capture.main())
""")
    metrics = json.loads(output)
    assert metrics["status"] == "benchmark_completed"
    assert metrics["frames_captured"] > 0
    assert metrics["backend"] == "FAKE"
    assert metrics["frames_delivered_to_ui"] > 0


def test_storage_and_network_benchmark_smoke():
    storage = json.loads(run_script("""
import sys, tempfile
from tests import benchmark_storage
with tempfile.TemporaryDirectory() as path:
    sys.argv = ['benchmark_storage', '--rows', '5', '--data-dir', path]
    raise SystemExit(benchmark_storage.main())
"""))
    assert storage["rows"] == storage["query_page_rows"] == 5
    assert storage["source"] == "synthetic"
    network = json.loads(run_script("""
import sys
from tests import benchmark_network
sys.argv = ['benchmark_network', '--reports', '5']
raise SystemExit(benchmark_network.main())
"""))
    assert network["sent"] == network["received"]
    assert network["produced"] == network["sent"] + network["dropped_stale"]
    assert network["source"] == "synthetic_loopback"
