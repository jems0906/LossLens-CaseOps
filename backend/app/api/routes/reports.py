import csv
import io
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
import sqlite3

from app.db import get_connection
from app.security.auth import Actor, current_actor
from app.services.audit_events import record_audit, utc_now
from app.services.reconciliation import calculate_reconciliation


router = APIRouter(prefix="/reports", tags=["reports"])


def week_start(timestamp: str) -> str:
    parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    return (parsed.date() - timedelta(days=parsed.weekday())).isoformat()


def median(values: list[float]) -> float | None:
    ordered = sorted(values)
    if not ordered:
        return None
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return round(ordered[middle], 1)
    return round((ordered[middle - 1] + ordered[middle]) / 2, 1)


@router.get("/leadership")
def leadership_summary(
    actor: Actor = Depends(current_actor),
    connection: sqlite3.Connection = Depends(get_connection),
) -> dict[str, object]:
    now = datetime.now(timezone.utc)
    today = now.date()
    buckets: dict[tuple[str, str, str], dict[str, list[dict[str, object]]]] = {}
    for row in connection.execute("SELECT * FROM events ORDER BY occurred_at"):
        key = (row["site_id"], row["process_step"], week_start(row["occurred_at"]))
        buckets.setdefault(key, {}).setdefault(row["reconciliation_id"], []).append(dict(row))
    trends: list[dict[str, object]] = []
    for (site, process, period), reconciliations in sorted(buckets.items()):
        results = [calculate_reconciliation(events) for events in reconciliations.values()]
        expected = sum(int(result["expected_units"]) for result in results)
        raw = sum(int(result["raw_discrepancy_units"]) for result in results)
        explained = sum(int(result["explained_units"]) for result in results)
        unexplained = sum(int(result["unexplained_units"]) for result in results)
        trends.append(
            {
                "site_id": site,
                "process_step": process,
                "week_start": period,
                "expected_units": expected,
                "eligible_processed_units": expected,
                "raw_discrepancy_units": raw,
                "explained_units": explained,
                "unexplained_units": unexplained,
                "discrepancy_rate": round(unexplained / expected, 4) if expected else None,
                "reconciliation_count": len(reconciliations),
                "classification": "unexplained_discrepancy" if unexplained else "resolved_reconciliation_issue" if raw else "no_discrepancy",
            }
        )

    cases = [dict(row) for row in connection.execute("SELECT * FROM cases")]
    open_cases = [case for case in cases if case["status"] != "closed"]
    closed_cases = [case for case in cases if case["status"] == "closed" and case["closed_at"]]
    open_ages = [
        max((now - datetime.fromisoformat(case["opened_at"])).total_seconds() / 86400, 0)
        for case in open_cases
    ]
    closure_days = [
        max((datetime.fromisoformat(case["closed_at"]) - datetime.fromisoformat(case["opened_at"])).total_seconds() / 86400, 0)
        for case in closed_cases
    ]
    month_start = today.replace(day=1).isoformat()
    due_actions = [
        dict(row)
        for row in connection.execute(
            "SELECT * FROM actions WHERE due_date >= ? AND due_date <= ?", (month_start, today.isoformat())
        )
    ]
    verified_actions = [action for action in due_actions if action["status"] == "completed" and action["verified_at"]]
    record_audit(connection, actor.actor_id, "accessed", "leadership_summary", "current")
    return {
        "as_of": now.isoformat(),
        "period_definition": "ISO week, grouped by fictional site and process; eligible processed units are the expected units entering that process step, and the rate is unexplained units / eligible processed units",
        "discrepancy_trends": trends,
        "case_aging": {
            "open_case_count": len(open_cases),
            "open_age_median_days": median(open_ages),
            "closed_case_count": len(closed_cases),
            "closed_age_median_days": median(closure_days),
        },
        "time_to_closure": {"sample_size": len(closure_days), "median_days": median(closure_days)},
        "action_completion": {
            "period_start": month_start,
            "period_end": today.isoformat(),
            "verified_completed": len(verified_actions),
            "actions_due": len(due_actions),
            "rate": round(len(verified_actions) / len(due_actions), 4) if due_actions else None,
        },
        "overdue_actions": connection.execute(
            "SELECT COUNT(*) FROM actions WHERE due_date < ? AND status != 'completed'", (today.isoformat(),)
        ).fetchone()[0],
        "recurring_process_issues": [
            {"process_step": row[0], "case_count": row[1]}
            for row in connection.execute(
                "SELECT process_step, COUNT(*) AS case_count FROM cases GROUP BY process_step HAVING COUNT(*) > 1"
            )
        ],
        "limitations": [
            "Synthetic operational records only; discrepancies are not findings of misconduct.",
            "A file hash can help detect a file change but does not establish authenticity, admissibility, or tamper-proof storage.",
            "Action completion is measured month-to-date using due dates and requires recorded verification evidence.",
            "No individual risk ranking or employee surveillance metrics are calculated.",
        ],
    }


@router.get("/reconciliation/{reconciliation_id}")
def reconciliation_detail(
    reconciliation_id: str,
    actor: Actor = Depends(current_actor),
    connection: sqlite3.Connection = Depends(get_connection),
) -> dict[str, object]:
    rows = [
        dict(row)
        for row in connection.execute(
            "SELECT * FROM events WHERE reconciliation_id = ? ORDER BY occurred_at", (reconciliation_id,)
        )
    ]
    result = calculate_reconciliation(rows)
    record_audit(connection, actor.actor_id, "accessed", "reconciliation", reconciliation_id)
    return {"reconciliation_id": reconciliation_id, "events": rows, **result}


@router.get("/cases.csv")
def export_cases(
    actor: Actor = Depends(current_actor),
    connection: sqlite3.Connection = Depends(get_connection),
) -> StreamingResponse:
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["case_id", "case_type", "report_source", "priority", "status", "site_id", "process_step", "opened_at", "closed_at", "simulated"])
    rows = connection.execute(
        "SELECT case_id, case_type, report_source, priority, status, site_id, process_step, opened_at, closed_at, simulated FROM cases ORDER BY opened_at"
    )
    writer.writerows([tuple(row) for row in rows])
    record_audit(connection, actor.actor_id, "exported", "cases_csv", "sanitized")
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=losslens_cases_synthetic.csv"})


@router.get("/events.csv")
def export_events(
    actor: Actor = Depends(current_actor),
    connection: sqlite3.Connection = Depends(get_connection),
) -> StreamingResponse:
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["event_id", "event_type", "process_step", "site_id", "occurred_at", "quantity", "source_ref", "reconciliation_id"])
    rows = connection.execute("SELECT * FROM events ORDER BY occurred_at")
    writer.writerows([tuple(row) for row in rows])
    record_audit(connection, actor.actor_id, "exported", "events_csv", "synthetic")
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=losslens_events_synthetic.csv"})