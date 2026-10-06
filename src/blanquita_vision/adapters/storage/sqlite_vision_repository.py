import csv
import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from ...application.report_mapper import calibration_in_mm
from ...domain.models.calibration import Calibration, CalibrationPoint, CalibrationStatus
from ...domain.models.geometry import ImagePoint, PhysicalPoint2D
from ...domain.models.protocol import utc_text
from ...infrastructure.schema import SCHEMA, SCHEMA_VERSION, TIME_COLUMNS
from ..calibration.opencv_homography_solver import OpenCvHomographySolver


class SQLiteVisionRepository:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.connection = None
        self.columns: dict[str, list[str]] = {}

    def open(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=0.1)
        self.connection = connection
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys=ON")
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if tables and "schema_meta" not in tables:
                raise ValueError("BD existente sin schema_meta: no se modifica automáticamente.")
            if "schema_meta" in tables:
                row = connection.execute("SELECT value FROM schema_meta WHERE key='schema_version'").fetchone()
                if row is None or row[0] != str(SCHEMA_VERSION):
                    raise ValueError("Versión de schema incompatible; no se escribirá en esta BD.")
                with sqlite3.connect(":memory:") as reference:
                    reference.executescript(SCHEMA)
                    for table in (*TIME_COLUMNS, "schema_meta", "app_settings", "calibration_points"):
                        expected = [tuple(row)[1:6] for row in reference.execute(f"PRAGMA table_info({table})")]
                        actual = [tuple(row)[1:6] for row in connection.execute(f"PRAGMA table_info({table})")]
                        if expected != actual:
                            raise ValueError(f"Schema incompatible en {table}; no se modificará la BD.")
            connection.execute("PRAGMA journal_mode=WAL")
            connection.executescript("BEGIN;\n" + SCHEMA +
                                     f"\nINSERT OR IGNORE INTO schema_meta VALUES('schema_version','{SCHEMA_VERSION}');\nCOMMIT;")
            for table in (*TIME_COLUMNS, "calibration_points", "app_settings"):
                self.columns[table] = [row[1] for row in connection.execute(f"PRAGMA table_info({table})")]
                if not self.columns[table]:
                    raise ValueError(f"Schema incompleto: falta {table}.")
        except Exception:
            connection.close()
            self.connection = None
            raise

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def _insert(self, table: str, record: dict) -> None:
        record = dict(record)
        if table not in self.columns or not record or any(key not in self.columns[table] for key in record):
            raise ValueError("Registro o tabla no permitido.")
        for key, value in record.items():
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError("Datos no finitos rechazados.")
            if key.endswith("_utc") and value is not None:
                record[key] = self._utc(value)
        names = list(record)
        self.connection.execute(f"INSERT INTO {table} ({','.join(names)}) VALUES ({','.join('?' for _ in names)})",
                                [record[name] for name in names])

    def insert(self, table: str, record: dict) -> None:
        with self.connection:
            self._insert(table, record)

    def create_session(self, record: dict) -> None:
        self.insert("vision_sessions", record)

    def close_session(self, session_id: str, ended_at_utc: str, reason: str) -> None:
        ended_at_utc = self._utc(ended_at_utc)
        with self.connection:
            self.connection.execute("UPDATE vision_sessions SET ended_at_utc=?,end_reason=? WHERE session_id=? AND ended_at_utc IS NULL",
                                    (ended_at_utc, reason, session_id))

    def save_detection(self, record: dict) -> None:
        self.insert("detections", record)

    def save_report(self, record: dict) -> None:
        self.insert("vision_reports", record)

    def save_metric_sample(self, record: dict) -> None:
        self.insert("metric_samples", record)

    def save_event(self, record: dict) -> None:
        self.insert("events", record)

    def save_error(self, record: dict) -> None:
        self.insert("errors", record)

    def save_calibration(self, calibration: Calibration) -> None:
        calibration = calibration_in_mm(calibration)
        record = dict(calibration_id=calibration.id, camera_id=calibration.camera_id,
                      width=calibration.width, height=calibration.height, unit="mm",
                      homography_json=json.dumps(calibration.homography, allow_nan=False),
                      created_at_utc=utc_text(calibration.created_at), status=calibration.status.value,
                      invalidated_at_utc=None)
        with self.connection:
            existing = self.connection.execute("SELECT * FROM calibrations WHERE calibration_id=?", (calibration.id,)).fetchone()
            if existing is not None:
                if any(existing[key] != value for key, value in record.items() if key not in ("status", "invalidated_at_utc")):
                    raise ValueError("Identificador de calibración existente con datos diferentes.")
                self.connection.execute("UPDATE calibrations SET status=?,invalidated_at_utc=NULL WHERE calibration_id=?",
                                        (calibration.status.value, calibration.id))
                return
            self._insert("calibrations", record)
            for index, point in enumerate(calibration.points, 1):
                self._insert("calibration_points", dict(calibration_id=calibration.id, point_order=index,
                                                        u=point.image.u, v=point.image.v,
                                                        x_mm=point.physical.x, y_mm=point.physical.y))

    def invalidate_calibration(self, calibration_id: str, timestamp: str) -> None:
        timestamp = self._utc(timestamp)
        with self.connection:
            self.connection.execute("UPDATE calibrations SET status='INVALID',invalidated_at_utc=? WHERE calibration_id=?",
                                    (timestamp, calibration_id))

    def invalidate_geometry(self, geometry: tuple, timestamp: str) -> None:
        timestamp = self._utc(timestamp)
        with self.connection:
            self.connection.execute("UPDATE calibrations SET status='INVALID',invalidated_at_utc=? WHERE camera_id=? AND width=? AND height=? AND status='VALID'",
                                    (timestamp, *geometry))

    def load_calibration(self, camera_id: str, width: int, height: int) -> Calibration | None:
        record = self.connection.execute(
            "SELECT * FROM calibrations WHERE camera_id=? AND width=? AND height=? AND status='VALID' ORDER BY created_at_utc DESC LIMIT 1",
            (camera_id, width, height)).fetchone()
        if record is None:
            return None
        rows = self.connection.execute("SELECT * FROM calibration_points WHERE calibration_id=? ORDER BY point_order",
                                       (record["calibration_id"],)).fetchall()
        points = tuple(CalibrationPoint(ImagePoint(row["u"], row["v"]),
                                        PhysicalPoint2D(row["x_mm"], row["y_mm"], "mm")) for row in rows)
        calibration = Calibration(record["calibration_id"], record["camera_id"], record["width"], record["height"],
                           points, tuple(tuple(row) for row in json.loads(record["homography_json"])), "mm",
                           datetime.fromisoformat(record["created_at_utc"]), CalibrationStatus.VALID)
        OpenCvHomographySolver().solve(points)
        matrix = np.asarray(calibration.homography, dtype=np.float64)
        scale = np.max(np.abs(matrix))
        if scale == 0 or np.linalg.matrix_rank(matrix / scale) < 3:
            raise ValueError("Homografía persistida singular.")
        return calibration

    @staticmethod
    def _utc(value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("Timestamp persistido inválido.")
        parsed = datetime.fromisoformat(value)
        if not value.endswith("Z") or parsed.tzinfo is None:
            raise ValueError("Persistencia requiere UTC/Z.")
        return utc_text(parsed)

    def load_settings(self) -> dict:
        return {row["key"]: json.loads(row["value_json"]) for row in self.connection.execute("SELECT * FROM app_settings")}

    def calibration_details(self, identifier: str) -> dict:
        row = self.connection.execute("SELECT * FROM calibrations WHERE calibration_id=?", (identifier,)).fetchone()
        if row is None:
            raise ValueError("Perfil de calibración no encontrado.")
        record = dict(row)
        record["points"] = [dict(point) for point in self.connection.execute(
            "SELECT * FROM calibration_points WHERE calibration_id=? ORDER BY point_order", (identifier,))]
        return record

    def save_settings(self, settings: dict) -> None:
        with self.connection:
            for key, value in settings.items():
                self.connection.execute("INSERT INTO app_settings VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json,updated_at_utc=excluded.updated_at_utc",
                                        (key, json.dumps(value, allow_nan=False), utc_text(datetime.now(timezone.utc))))

    def query(self, category: str, filters: dict, limit: int = 50, offset: int = 0) -> list[dict]:
        if category not in TIME_COLUMNS or not 1 <= limit <= 1000 or offset < 0:
            raise ValueError("Consulta no válida.")
        terms, values = [], []
        time_column = TIME_COLUMNS[category]
        for key, operator in (("start", ">="), ("end", "<=")):
            if filters.get(key):
                terms.append(f"{time_column}{operator}?")
                values.append(filters[key])
        if filters.get("session_id"):
            column = "session_id"
            if column not in self.columns[category]:
                raise ValueError("Esta categoría no se filtra por sesión.")
            terms.append("session_id=?")
            values.append(filters["session_id"])
        if filters.get("search"):
            searchable = [column for column in self.columns[category]
                          if column in ("message", "object_name", "code", "event_type", "relative_path", "end_reason", "session_id", "calibration_id")]
            if searchable:
                terms.append("(" + " OR ".join(f"{column} LIKE ?" for column in searchable) + ")")
                values.extend([f"%{filters['search']}%"] * len(searchable))
        where = " WHERE " + " AND ".join(terms) if terms else ""
        primary = self.columns[category][0]
        rows = self.connection.execute(f"SELECT * FROM {category}{where} ORDER BY {time_column} DESC,{primary} DESC LIMIT ? OFFSET ?",
                                       (*values, limit, offset)).fetchall()
        return [dict(row) for row in rows]

    def export(self, category: str, filters: dict, path: Path, format: str) -> int:
        if category not in TIME_COLUMNS or format not in ("json", "csv"):
            raise ValueError("Exportación inválida.")
        count = 0
        with self.connection:
            self.connection.execute("BEGIN")
            with Path(path).open("w", encoding="utf-8", newline="") as output:
                writer = csv.DictWriter(output, fieldnames=self.columns[category]) if format == "csv" else None
                if writer:
                    writer.writeheader()
                else:
                    output.write("[\n")
                while True:
                    rows = self.query(category, filters, 50, count)
                    if not rows:
                        break
                    for row in rows:
                        if writer:
                            writer.writerow(row)
                        else:
                            output.write((",\n" if count else "") + json.dumps(row, ensure_ascii=False, allow_nan=False))
                        count += 1
                if not writer:
                    output.write("\n]\n")
        return count

    def health(self) -> dict:
        return dict(path=str(self.path), wal=self.connection.execute("PRAGMA journal_mode").fetchone()[0],
                    schema_version=SCHEMA_VERSION, size_bytes=self.path.stat().st_size,
                    settings=self.load_settings())
