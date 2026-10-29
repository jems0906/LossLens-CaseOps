import json
from datetime import datetime, timezone
from uuid import uuid4

import sqlite3


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_audit(
    connection: sqlite3.Connection,
    actor: str,
    action: str,
    entity: str,
    entity_id: str,
    metadata: dict[str, object] | None = None,
) -> None:
    connection.execute(
        "INSERT INTO audit_events VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            str(uuid4()),
            actor,
            action,
            entity,
            entity_id,
            json.dumps(metadata or {}, sort_keys=True),
            utc_now(),
        ),
    )