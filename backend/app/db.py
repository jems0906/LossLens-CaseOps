import sqlite3
from collections.abc import Iterator

from app.config import DB_PATH


SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    process_step TEXT NOT NULL,
    site_id TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    source_ref TEXT NOT NULL,
    reconciliation_id TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS cases (
    case_id TEXT PRIMARY KEY,
    case_type TEXT NOT NULL,
    report_source TEXT NOT NULL,
    priority TEXT NOT NULL,
    owner TEXT NOT NULL,
    status TEXT NOT NULL,
    concern TEXT NOT NULL,
    report_summary TEXT,
    simulated INTEGER NOT NULL DEFAULT 1,
    site_id TEXT NOT NULL,
    process_step TEXT NOT NULL,
    reconciliation_id TEXT,
    opened_at TEXT NOT NULL,
    closed_at TEXT,
    resolution TEXT
);
CREATE TABLE IF NOT EXISTS evidence (
    evidence_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(case_id),
    source_ref TEXT NOT NULL,
    collector TEXT NOT NULL,
    collection_time TEXT NOT NULL,
    event_time TEXT,
    file_hash TEXT,
    notes TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS timeline (
    entry_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(case_id),
    category TEXT NOT NULL,
    summary TEXT NOT NULL,
    details TEXT NOT NULL,
    recorded_by TEXT NOT NULL,
    event_time TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS interview_notes (
    note_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(case_id),
    interviewee_role TEXT NOT NULL,
    interview_date TEXT,
    topics TEXT NOT NULL,
    notes TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS actions (
    action_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(case_id),
    process_change TEXT NOT NULL,
    owner TEXT NOT NULL,
    due_date TEXT NOT NULL,
    status TEXT NOT NULL,
    verification_evidence TEXT,
    created_at TEXT NOT NULL,
    verified_at TEXT
);
CREATE TABLE IF NOT EXISTS audit_events (
    audit_id TEXT PRIMARY KEY,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    entity TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    occurred_at TEXT NOT NULL
);
"""


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database() -> None:
    with connect() as connection:
        connection.executescript(SCHEMA)


def get_connection() -> Iterator[sqlite3.Connection]:
    connection = connect()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()