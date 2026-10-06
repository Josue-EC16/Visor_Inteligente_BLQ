"""TC-02-062: benchmark sintético de SQLite, sin hardware ni objetivos inventados."""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from blanquita_vision.adapters.storage.sqlite_vision_repository import SQLiteVisionRepository
from blanquita_vision.domain.models.protocol import utc_text


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark sintético SQLite")
    parser.add_argument("--rows", type=int, required=True)
    parser.add_argument("--data-dir", required=True)
    args = parser.parse_args()
    if args.rows < 1:
        parser.error("Se requiere al menos una fila.")
    repository = SQLiteVisionRepository(Path(args.data_dir) / "benchmark_storage.db")
    started = perf_counter()
    try:
        repository.open()
        identifier = str(uuid4())
        repository.create_session(dict(session_id=identifier, started_at_utc=utc_text(datetime.now(timezone.utc)),
                                       start_source="local_ui"))
        writing = perf_counter()
        for sequence in range(args.rows):
            repository.save_detection(dict(session_id=identifier, frame_sequence=sequence,
                                            timestamp_utc=utc_text(datetime.now(timezone.utc)), detected=0,
                                            object_name="gancho", confidence=0.0))
        writes_seconds = perf_counter() - writing
        query_started = perf_counter()
        page = repository.query("detections", {"session_id": identifier}, 50, 0)
        query_seconds = perf_counter() - query_started
        repository.close_session(identifier, utc_text(datetime.now(timezone.utc)), "benchmark")
        health = repository.health()
        print(json.dumps(dict(status="completed", source="synthetic", rows=args.rows,
                              write_seconds=writes_seconds, writes_per_second=args.rows / writes_seconds,
                              query_page_rows=len(page), query_seconds=query_seconds, database_bytes=health["size_bytes"],
                              wal_bytes=Path(str(repository.path) + "-wal").stat().st_size,
                              total_seconds=perf_counter() - started, database_path=str(repository.path)), indent=2))
        return 0
    finally:
        repository.close()


if __name__ == "__main__":
    raise SystemExit(main())
