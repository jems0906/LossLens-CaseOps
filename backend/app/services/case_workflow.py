import sqlite3

from app.services.audit_events import utc_now


class WorkflowTransitionError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _case_for_transition(connection: sqlite3.Connection, case_id: str) -> sqlite3.Row:
    case = connection.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,)).fetchone()
    if case is None:
        raise WorkflowTransitionError(404, "Case not found")
    return case


def submit_case(connection: sqlite3.Connection, case_id: str) -> sqlite3.Row:
    case = _case_for_transition(connection, case_id)
    if case["status"] != "draft":
        raise WorkflowTransitionError(409, "Only draft cases can be submitted")
    connection.execute("UPDATE cases SET status = 'review' WHERE case_id = ?", (case_id,))
    return _case_for_transition(connection, case_id)


def approve_case(connection: sqlite3.Connection, case_id: str) -> sqlite3.Row:
    case = _case_for_transition(connection, case_id)
    if case["status"] != "review":
        raise WorkflowTransitionError(409, "Only cases in review can be approved")
    if not (case["report_summary"] or "").strip():
        raise WorkflowTransitionError(409, "A documented report summary is required before approval")
    connection.execute("UPDATE cases SET status = 'approved_report' WHERE case_id = ?", (case_id,))
    return _case_for_transition(connection, case_id)


def close_case(
    connection: sqlite3.Connection,
    case_id: str,
    resolution: str,
) -> sqlite3.Row:
    case = _case_for_transition(connection, case_id)
    if case["status"] != "approved_report":
        raise WorkflowTransitionError(
            409,
            "A reviewer-approved report is required before closure",
        )
    connection.execute(
        "UPDATE cases SET status = 'closed', closed_at = ?, resolution = ? WHERE case_id = ?",
        (utc_now(), resolution, case_id),
    )
    return _case_for_transition(connection, case_id)