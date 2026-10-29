from datetime import datetime
import re
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
import sqlite3

from app.api.routes.cases import get_case
from app.db import get_connection
from app.schemas import EvidenceCreate, EvidenceUpdate
from app.security.auth import Actor, current_actor
from app.services.audit_events import record_audit, utc_now


router = APIRouter(prefix="/cases/{case_id}/evidence", tags=["evidence"])
HASH_PATTERN = re.compile(r"^[a-fA-F0-9]{64}$")


def validate_timestamp(value: str | None, field: str) -> str | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise HTTPException(status_code=422, detail=f"{field} must be an ISO 8601 timestamp") from error
    if parsed.tzinfo is None:
        raise HTTPException(status_code=422, detail=f"{field} must include a timezone")
    return parsed.isoformat()


def validate_hash(value: str | None) -> str | None:
    if value is not None and not HASH_PATTERN.fullmatch(value):
        raise HTTPException(status_code=422, detail="file_hash must be a 64-character SHA-256 hex digest")
    return value.lower() if value else None


@router.get("")
def list_evidence(
    case_id: str,
    actor: Actor = Depends(current_actor),
    connection: sqlite3.Connection = Depends(get_connection),
) -> list[dict[str, object]]:
    get_case(connection, case_id)
    rows = [dict(row) for row in connection.execute("SELECT * FROM evidence WHERE case_id = ?", (case_id,))]
    record_audit(connection, actor.actor_id, "accessed", "evidence_register", case_id, {"count": len(rows)})
    return rows


@router.post("", status_code=201)
def add_evidence(
    case_id: str,
    payload: EvidenceCreate,
    actor: Actor = Depends(current_actor),
    connection: sqlite3.Connection = Depends(get_connection),
) -> dict[str, object]:
    get_case(connection, case_id)
    evidence_id = str(uuid4())
    collection_time = validate_timestamp(payload.collection_time, "collection_time")
    event_time = validate_timestamp(payload.event_time, "event_time")
    file_hash = validate_hash(payload.file_hash)
    connection.execute(
        "INSERT INTO evidence VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (evidence_id, case_id, payload.source_ref, payload.collector, collection_time, event_time,
         file_hash, payload.notes, utc_now()),
    )
    record_audit(connection, actor.actor_id, "created", "evidence", evidence_id, {"case_id": case_id})
    return dict(connection.execute("SELECT * FROM evidence WHERE evidence_id = ?", (evidence_id,)).fetchone())


@router.patch("/{evidence_id}")
def update_evidence(
    case_id: str,
    evidence_id: str,
    payload: EvidenceUpdate,
    actor: Actor = Depends(current_actor),
    connection: sqlite3.Connection = Depends(get_connection),
) -> dict[str, object]:
    get_case(connection, case_id)
    existing = connection.execute(
        "SELECT * FROM evidence WHERE evidence_id = ? AND case_id = ?", (evidence_id, case_id)
    ).fetchone()
    if existing is None:
        raise HTTPException(status_code=404, detail="Evidence item not found")
    changes = payload.model_dump(exclude_unset=True)
    required_metadata = {"source_ref", "collector", "collection_time", "notes"}
    if any(field in changes and changes[field] is None for field in required_metadata):
        raise HTTPException(status_code=422, detail="Required evidence metadata cannot be null")
    if "collection_time" in changes:
        changes["collection_time"] = validate_timestamp(changes["collection_time"], "collection_time")
    if "event_time" in changes:
        changes["event_time"] = validate_timestamp(changes["event_time"], "event_time")
    if "file_hash" in changes:
        changes["file_hash"] = validate_hash(changes["file_hash"])
    if not changes:
        raise HTTPException(status_code=400, detail="No evidence metadata supplied")
    assignments = ", ".join(f"{field} = ?" for field in changes)
    connection.execute(
        f"UPDATE evidence SET {assignments} WHERE evidence_id = ?",
        [*changes.values(), evidence_id],
    )
    record_audit(connection, actor.actor_id, "updated_metadata", "evidence", evidence_id, changes)
    return dict(connection.execute("SELECT * FROM evidence WHERE evidence_id = ?", (evidence_id,)).fetchone())