from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
import sqlite3

from app.db import get_connection
from app.schemas import CaseCreate, CaseUpdate, InterviewNoteCreate, TimelineCreate
from app.security.auth import Actor, current_actor
from app.services.audit_events import record_audit, utc_now


router = APIRouter(prefix="/cases", tags=["cases"])


def get_case(connection: sqlite3.Connection, case_id: str) -> sqlite3.Row:
    case = connection.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,)).fetchone()
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@router.get("")
def list_cases(
    actor: Actor = Depends(current_actor),
    connection: sqlite3.Connection = Depends(get_connection),
) -> list[dict[str, object]]:
    del actor
    return [dict(row) for row in connection.execute("SELECT * FROM cases ORDER BY opened_at DESC")]


@router.post("", status_code=201)
def create_case(
    payload: CaseCreate,
    actor: Actor = Depends(current_actor),
    connection: sqlite3.Connection = Depends(get_connection),
) -> dict[str, object]:
    case_id = payload.case_id or f"CASE-{uuid4().hex[:8].upper()}"
    try:
        connection.execute(
            """INSERT INTO cases
            (case_id, case_type, report_source, priority, owner, status, concern,
             simulated, site_id, process_step, reconciliation_id, opened_at)
            VALUES (?, ?, ?, ?, ?, 'draft', ?, ?, ?, ?, ?, ?)""",
            (
                case_id,
                payload.case_type,
                payload.report_source,
                payload.priority,
                payload.owner,
                payload.concern,
                int(payload.simulated),
                payload.site_id,
                payload.process_step,
                payload.reconciliation_id,
                utc_now(),
            ),
        )
    except sqlite3.IntegrityError as error:
        raise HTTPException(status_code=409, detail="Case ID already exists") from error
    record_audit(connection, actor.actor_id, "created", "case", case_id)
    return dict(get_case(connection, case_id))


@router.get("/{case_id}")
def read_case(
    case_id: str,
    actor: Actor = Depends(current_actor),
    connection: sqlite3.Connection = Depends(get_connection),
) -> dict[str, object]:
    del actor
    return dict(get_case(connection, case_id))


@router.patch("/{case_id}")
def update_case(
    case_id: str,
    payload: CaseUpdate,
    actor: Actor = Depends(current_actor),
    connection: sqlite3.Connection = Depends(get_connection),
) -> dict[str, object]:
    case = get_case(connection, case_id)
    if case["status"] in {"approved_report", "closed"}:
        raise HTTPException(status_code=409, detail="Approved or closed case fields cannot be edited")
    changes = {
        field: value
        for field, value in payload.model_dump(exclude_unset=True).items()
        if value is not None
    }
    if not changes:
        raise HTTPException(status_code=400, detail="No case fields supplied")
    assignments = ", ".join(f"{field} = ?" for field in changes)
    connection.execute(
        f"UPDATE cases SET {assignments} WHERE case_id = ?",
        [*changes.values(), case_id],
    )
    record_audit(connection, actor.actor_id, "updated", "case", case_id, changes)
    return dict(get_case(connection, case_id))


@router.get("/{case_id}/timeline")
def list_timeline(
    case_id: str,
    actor: Actor = Depends(current_actor),
    connection: sqlite3.Connection = Depends(get_connection),
) -> list[dict[str, object]]:
    del actor
    get_case(connection, case_id)
    return [
        dict(row)
        for row in connection.execute(
            "SELECT * FROM timeline WHERE case_id = ? ORDER BY COALESCE(event_time, created_at)",
            (case_id,),
        )
    ]


@router.post("/{case_id}/timeline", status_code=201)
def add_timeline_entry(
    case_id: str,
    payload: TimelineCreate,
    actor: Actor = Depends(current_actor),
    connection: sqlite3.Connection = Depends(get_connection),
) -> dict[str, object]:
    get_case(connection, case_id)
    event_time = payload.event_time
    if event_time:
        try:
            parsed_time = datetime.fromisoformat(event_time.replace("Z", "+00:00"))
        except ValueError as error:
            raise HTTPException(status_code=422, detail="event_time must be an ISO 8601 timestamp") from error
        if parsed_time.tzinfo is None:
            raise HTTPException(status_code=422, detail="event_time must include a timezone")
        event_time = parsed_time.astimezone(timezone.utc).isoformat()
    entry_id = str(uuid4())
    created_at = utc_now()
    connection.execute(
        "INSERT INTO timeline VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (entry_id, case_id, payload.category, payload.summary, payload.details, actor.actor_id, event_time, created_at),
    )
    record_audit(connection, actor.actor_id, "created", "timeline_entry", entry_id, {"case_id": case_id})
    return dict(connection.execute("SELECT * FROM timeline WHERE entry_id = ?", (entry_id,)).fetchone())


@router.get("/{case_id}/interview-guide")
def interview_guide(
    case_id: str,
    actor: Actor = Depends(current_actor),
) -> dict[str, object]:
    del actor
    questions = [
        "Please walk me through your understanding of the receiving handoff.",
        "What records or tools did you use, and what did each show at the time?",
        "Were there delays, corrections, damage reports, or other context we should include?",
        "What would help us verify the sequence of events?",
        "Is there anything in our summary that you would correct or clarify?",
    ]
    return {
        "case_id": case_id,
        "questions": questions,
        "note_fields": ["interviewee_role", "interview_date", "topics", "notes"],
        "guardrails": "Open-ended and non-coercive. Do not score credibility or infer guilt.",
    }


@router.post("/{case_id}/interview-notes", status_code=201)
def add_interview_note(
    case_id: str,
    payload: InterviewNoteCreate,
    actor: Actor = Depends(current_actor),
    connection: sqlite3.Connection = Depends(get_connection),
) -> dict[str, object]:
    get_case(connection, case_id)
    note_id = str(uuid4())
    connection.execute(
        "INSERT INTO interview_notes VALUES (?, ?, ?, ?, ?, ?, ?)",
        (note_id, case_id, payload.interviewee_role, payload.interview_date.isoformat() if payload.interview_date else None,
         payload.topics, payload.notes, utc_now()),
    )
    record_audit(connection, actor.actor_id, "created", "interview_note", note_id, {"case_id": case_id})
    return dict(connection.execute("SELECT * FROM interview_notes WHERE note_id = ?", (note_id,)).fetchone())


@router.get("/{case_id}/interview-notes")
def list_interview_notes(
    case_id: str,
    actor: Actor = Depends(current_actor),
    connection: sqlite3.Connection = Depends(get_connection),
) -> list[dict[str, object]]:
    del actor
    get_case(connection, case_id)
    return [dict(row) for row in connection.execute("SELECT * FROM interview_notes WHERE case_id = ?", (case_id,))]