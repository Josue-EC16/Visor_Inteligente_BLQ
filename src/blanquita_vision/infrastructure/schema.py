SCHEMA_VERSION = 1

SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS app_settings(key TEXT PRIMARY KEY, value_json TEXT NOT NULL, updated_at_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS vision_sessions(
 session_id TEXT PRIMARY KEY, started_at_utc TEXT NOT NULL, ended_at_utc TEXT,
 start_source TEXT NOT NULL CHECK(start_source IN ('local_ui','mobile')), end_reason TEXT,
 camera_id TEXT, width INTEGER, height INTEGER);
CREATE INDEX IF NOT EXISTS session_started ON vision_sessions(started_at_utc);
CREATE INDEX IF NOT EXISTS session_ended ON vision_sessions(ended_at_utc);
CREATE TABLE IF NOT EXISTS calibrations(
 calibration_id TEXT PRIMARY KEY, camera_id TEXT NOT NULL, width INTEGER NOT NULL,
 height INTEGER NOT NULL, unit TEXT NOT NULL CHECK(unit='mm'), homography_json TEXT NOT NULL,
 created_at_utc TEXT NOT NULL, status TEXT NOT NULL, invalidated_at_utc TEXT);
CREATE INDEX IF NOT EXISTS calibration_match ON calibrations(camera_id,width,height,status,created_at_utc);
CREATE TABLE IF NOT EXISTS calibration_points(
 calibration_id TEXT NOT NULL REFERENCES calibrations(calibration_id),
 point_order INTEGER NOT NULL CHECK(point_order BETWEEN 1 AND 4), u REAL NOT NULL, v REAL NOT NULL,
 x_mm REAL NOT NULL, y_mm REAL NOT NULL, PRIMARY KEY(calibration_id,point_order));
CREATE TABLE IF NOT EXISTS detections(
 detection_id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT REFERENCES vision_sessions(session_id),
 frame_sequence INTEGER NOT NULL, timestamp_utc TEXT NOT NULL, detected INTEGER NOT NULL,
 object_name TEXT NOT NULL, confidence REAL NOT NULL CHECK(confidence BETWEEN 0 AND 1),
 bbox_x REAL, bbox_y REAL, bbox_w REAL, bbox_h REAL, centroid_u REAL, centroid_v REAL,
 tracking_state TEXT, tracking_source TEXT, raw_x_mm REAL, raw_y_mm REAL,
 filtered_x_mm REAL, filtered_y_mm REAL, z_mm REAL, calibration_id TEXT REFERENCES calibrations(calibration_id));
CREATE INDEX IF NOT EXISTS detection_session_time ON detections(session_id,timestamp_utc);
CREATE INDEX IF NOT EXISTS detection_time ON detections(timestamp_utc);
CREATE INDEX IF NOT EXISTS detection_presence ON detections(detected);
CREATE TABLE IF NOT EXISTS vision_reports(
 message_id TEXT PRIMARY KEY, session_id TEXT REFERENCES vision_sessions(session_id), frame_sequence INTEGER NOT NULL,
 envelope_timestamp_utc TEXT NOT NULL, observation_timestamp_utc TEXT NOT NULL,
 detected INTEGER NOT NULL, object_name TEXT NOT NULL, x_mm REAL, y_mm REAL, z_mm REAL, angle REAL,
 confidence REAL NOT NULL, calibration_status TEXT NOT NULL, tracking_state TEXT NOT NULL, payload_json TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS report_session_time ON vision_reports(session_id,observation_timestamp_utc);
CREATE TABLE IF NOT EXISTS captures(
 capture_id TEXT PRIMARY KEY, session_id TEXT REFERENCES vision_sessions(session_id), created_at_utc TEXT NOT NULL,
 relative_path TEXT NOT NULL UNIQUE, format TEXT NOT NULL CHECK(format IN ('jpg','png')),
 frame_sequence INTEGER, detected INTEGER, confidence REAL, x_mm REAL, y_mm REAL, z_mm REAL);
CREATE TABLE IF NOT EXISTS metric_samples(
 metric_id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL REFERENCES vision_sessions(session_id),
 window_start_utc TEXT NOT NULL, window_end_utc TEXT NOT NULL, capture_fps_avg REAL, pipeline_fps_avg REAL,
 preprocess_ms_avg REAL, detection_ms_avg REAL, tracking_ms_avg REAL, position_ms_avg REAL, filter_ms_avg REAL,
 total_ms_avg REAL, confidence_avg REAL, detections_count INTEGER NOT NULL DEFAULT 0,
 tracking_lost_count INTEGER NOT NULL DEFAULT 0, reacquisitions_count INTEGER NOT NULL DEFAULT 0,
 errors_count INTEGER NOT NULL DEFAULT 0, raw_x_avg_mm REAL, raw_y_avg_mm REAL, filtered_x_avg_mm REAL, filtered_y_avg_mm REAL);
CREATE INDEX IF NOT EXISTS metric_session_time ON metric_samples(session_id,window_start_utc);
CREATE TABLE IF NOT EXISTS events(
 event_id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT REFERENCES vision_sessions(session_id), timestamp_utc TEXT NOT NULL,
 category TEXT NOT NULL, event_type TEXT NOT NULL, severity TEXT NOT NULL, message TEXT NOT NULL, metadata_json TEXT);
CREATE TABLE IF NOT EXISTS errors(
 error_id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT REFERENCES vision_sessions(session_id), timestamp_utc TEXT NOT NULL,
 component TEXT NOT NULL, code TEXT NOT NULL, message TEXT NOT NULL, recoverable INTEGER NOT NULL, details_json TEXT);
"""

TIME_COLUMNS = {
    "vision_sessions": "started_at_utc", "calibrations": "created_at_utc", "detections": "timestamp_utc",
    "vision_reports": "observation_timestamp_utc", "captures": "created_at_utc",
    "metric_samples": "window_start_utc", "events": "timestamp_utc", "errors": "timestamp_utc",
}
