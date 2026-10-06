import ast
import sys
import tomllib
from importlib.metadata import distributions, version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_tc_020_domain_and_application_do_not_import_concrete_technologies():
    forbidden = {"PySide6", "cv2", "sqlite3", "websockets", "onnxruntime"}
    for layer in ("domain", "application"):
        for path in (ROOT / "src" / "blanquita_vision" / layer).rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    assert not any(item.name.split(".")[0] in forbidden for item in node.names)
                elif isinstance(node, ast.ImportFrom):
                    assert (node.module or "").split(".")[0] not in forbidden


def test_exact_environment_and_single_opencv_distribution():
    assert sys.version_info[:3] == (3, 13, 16)
    expected = {"PySide6": "6.11.2", "pyqtgraph": "0.14.0", "numpy": "2.5.3",
                "opencv-contrib-python-headless": "4.14.0.94", "pytest": "9.1.1",
                "pydantic": "2.13.5", "websockets": "17.1"}
    for package, pinned in expected.items():
        assert version(package) == pinned
    opencv = [d.metadata["Name"].lower() for d in distributions()
              if d.metadata["Name"].lower().startswith("opencv-")]
    assert opencv == ["opencv-contrib-python-headless"]


def test_lock_and_requirements_match_direct_pins():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    locked = {p["name"]: p["version"] for p in lock["package"]}
    exported = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    dependencies = project["project"]["dependencies"] + project["dependency-groups"]["dev"]
    for dependency in dependencies:
        name, pinned = dependency.split("==")
        assert locked[name.lower()] == pinned
        assert f"{name.lower()}=={pinned}" in exported
