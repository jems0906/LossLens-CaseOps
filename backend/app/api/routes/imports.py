import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
import sqlite3

from app.db import get_connection
from app.security.auth import Actor, current_actor
from app.services.audit_events import record_audit


router = APIRouter(prefix="/imports", tags=["imports"])
REQUIRED_FIELDS = {
    "event_id",
    "event_type",
    "process_step",
    "site_id",
    "occurred_at",
    "quantity",
    "source_ref",
    "reconciliation_id",
}
EVENT_TYPES = {
    "shipment",
    "receipt",
    "receipt_correction",
    "transfer_in",
    "transfer_out",
    "return",
    "damage_adjustment",
    "inventory_adjustment",
}


@router.post("/events")
async def import_events(
    file: UploadFile = File(...),
    actor: Actor = Depends(current_actor),
    connection: sqlite3.Connection = Depends(get_connection),
) -> dict[str, object]:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Upload a CSV file")
    payload = await file.read(5_000_001)
    if len(payload) > 5_000_000:
        raise HTTPException(status_code=413, detail="CSV exceeds the 5 MB limit")
    try:
        reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig")))
        headers = set(reader.fieldnames or [])
    except (UnicodeDecodeError, csv.Error) as error:
        raise HTTPException(status_code=400, detail="CSV must be valid UTF-8") from error
    missing = sorted(REQUIRED_FIELDS - headers)
    if missing:
        raise HTTPException(
            status_code=422,
            detail={"message": "Required columns are missing", "columns": missing},
        )

    rows: list[tuple[str, ...]] = []
    issues: list[dict[str, object]] = []
    seen: set[str] = set()
    for row_number, row in enumerate(reader, start=2):
        event_id = (row.get("event_id") or "").strip()
        if not event_id:
            issues.append({"row": row_number, "field": "event_id", "issue": "required"})
            continue
        if event_id in seen:
            issues.append({"row": row_number, "field": "event_id", "issue": "duplicate in file"})
            continue
        seen.add(event_id)
        if connection.execute("SELECT 1 FROM events WHERE event_id = ?", (event_id,)).fetchone():
            issues.append({"row": row_number, "field": "event_id", "issue": "already imported"})
            continue

        required_text = [
            "event_type",
            "process_step",
            "site_id",
            "occurred_at",
            "quantity",
            "source_ref",
            "reconciliation_id",
        ]
        blank = [field for field in required_text if not (row.get(field) or "").strip()]
        if blank:
            issues.extend({"row": row_number, "field": field, "issue": "required"} for field in blank)
            continue
        event_type = row["event_type"].strip()
        if event_type not in EVENT_TYPES:
            issues.append({"row": row_number, "field": "event_type", "issue": "unsupported value"})
            continue
        try:
            quantity = int(row["quantity"])
            if quantity <= 0:
                raise ValueError
        except ValueError:
            issues.append({"row": row_number, "field": "quantity", "issue": "must be a positive integer"})
            continue
        try:
            occurred = datetime.fromisoformat(row["occurred_at"].strip().replace("Z", "+00:00"))
            if occurred.tzinfo is None:
                raise ValueError
            normalized_time = occurred.astimezone(timezone.utc).isoformat()
        except ValueError:
            issues.append({"row": row_number, "field": "occurred_at", "issue": "must be an ISO 8601 timestamp with timezone"})
            continue
        rows.append(
            (
                event_id,
                event_type,
                row["process_step"].strip(),
                row["site_id"].strip(),
                normalized_time,
                quantity,
                row["source_ref"].strip(),
                row["reconciliation_id"].strip(),
            )
        )
    if issues:
        raise HTTPException(status_code=422, detail={"message": "No rows imported", "issues": issues})
    if not rows:
        raise HTTPException(status_code=422, detail="CSV contains no event rows")

    connection.executemany(
        "INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows
    )
    record_audit(connection, actor.actor_id, "imported", "events", file.filename, {"row_count": len(rows)})
    return {"imported": len(rows), "event_ids": [row[0] for row in rows]}