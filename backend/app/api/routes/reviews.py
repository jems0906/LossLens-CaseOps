from datetime import date
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
import sqlite3

from app.api.routes.cases import get_case
from app.db import get_connection
from app.schemas import ActionCreate, ActionUpdate, CloseCase
from app.security.auth import Actor, current_actor, reviewer_actor
from app.services.audit_events import record_audit, utc_now
from app.services.case_workflow import (
    WorkflowTransitionError,
    approve_case as transition_approve_case,
    close_case as transition_close_case,
    submit_case,
)


router = APIRouter(tags=["reviews"])


@router.post("/cases/{case_id}/reviews/submit")
def submit_for_review(
    case_id: str,
    actor: Actor = Depends(current_actor),
    connection: sqlite3.Connection = Depends(get_connection),
) -> dict[str, object]:
    try:
        case = submit_case(connection, case_id)
    except WorkflowTransitionError as error:
        raise HTTPException(status_code=error.status_code, detail=error.detail) from error
    record_audit(connection, actor.actor_id, "submitted_for_review", "case", case_id)
    return dict(case)


@router.post("/cases/{case_id}/reviews/approve")
def approve_case(
    case_id: str,
    actor: Actor = Depends(reviewer_actor),
    connection: sqlite3.Connection = Depends(get_connection),
) -> dict[str, object]:
    try:
        case = transition_approve_case(connection, case_id)
    except WorkflowTransitionError as error:
        raise HTTPException(status_code=error.status_code, detail=error.detail) from error
    record_audit(connection, actor.actor_id, "approved_report", "case", case_id)
    return dict(case)


@router.post("/cases/{case_id}/reviews/close")
def close_case(
    case_id: str,
    payload: CloseCase,
    actor: Actor = Depends(reviewer_actor),
    connection: sqlite3.Connection = Depends(get_connection),
) -> dict[str, object]:
    try:
        case = transition_close_case(connection, case_id, payload.resolution)
    except WorkflowTransitionError as error:
        raise HTTPException(status_code=error.status_code, detail=error.detail) from error
    record_audit(connection, actor.actor_id, "closed", "case", case_id)
    return dict(case)


@router.post("/cases/{case_id}/actions", status_code=201)
def create_action(
    case_id: str,
    payload: ActionCreate,
    actor: Actor = Depends(current_actor),
    connection: sqlite3.Connection = Depends(get_connection),
) -> dict[str, object]:
    get_case(connection, case_id)
    action_id = str(uuid4())
    connection.execute(
        "INSERT INTO actions VALUES (?, ?, ?, ?, ?, 'open', NULL, ?, NULL)",
        (action_id, case_id, payload.process_change, payload.owner, payload.due_date.isoformat(), utc_now()),
    )
    record_audit(connection, actor.actor_id, "created", "mitigation_action", action_id, {"case_id": case_id})
    return dict(connection.execute("SELECT * FROM actions WHERE action_id = ?", (action_id,)).fetchone())


@router.get("/cases/{case_id}/actions")
def list_actions(
    case_id: str,
    actor: Actor = Depends(current_actor),
    connection: sqlite3.Connection = Depends(get_connection),
) -> list[dict[str, object]]:
    del actor
    get_case(connection, case_id)
    return [dict(row) for row in connection.execute("SELECT * FROM actions WHERE case_id = ?", (case_id,))]


@router.patch("/actions/{action_id}")
def update_action(
    action_id: str,
    payload: ActionUpdate,
    actor: Actor = Depends(current_actor),
    connection: sqlite3.Connection = Depends(get_connection),
) -> dict[str, object]:
    action = connection.execute("SELECT * FROM actions WHERE action_id = ?", (action_id,)).fetchone()
    if action is None:
        raise HTTPException(status_code=404, detail="Action not found")
    if payload.status == "completed" and not (payload.verification_evidence or "").strip():
        raise HTTPException(status_code=422, detail="Verification evidence is required to complete an action")
    verified_at = utc_now() if payload.status == "completed" else None
    connection.execute(
        "UPDATE actions SET status = ?, verification_evidence = ?, verified_at = ? WHERE action_id = ?",
        (payload.status, payload.verification_evidence, verified_at, action_id),
    )
    record_audit(connection, actor.actor_id, "updated", "mitigation_action", action_id, payload.model_dump())
    return dict(connection.execute("SELECT * FROM actions WHERE action_id = ?", (action_id,)).fetchone())