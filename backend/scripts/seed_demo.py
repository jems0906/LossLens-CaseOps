from pathlib import Path
import csv
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import connect, initialize_database
from app.services.audit_events import record_audit, utc_now


ROOT = Path(__file__).resolve().parents[2]
EVENT_FIXTURES = (
    "synthetic_inventory_events.csv",
    "synthetic_transfer_events.csv",
    "synthetic_return_events.csv",
    "synthetic_adjustment_events.csv",
)


def load_synthetic_events() -> list[tuple[str, str, str, str, str, int, str, str]]:
    events = []
    for filename in EVENT_FIXTURES:
        with (ROOT / "fixtures" / filename).open(encoding="utf-8-sig", newline="") as source:
            for row in csv.DictReader(source):
                events.append(
                    (
                        row["event_id"],
                        row["event_type"],
                        row["process_step"],
                        row["site_id"],
                        row["occurred_at"],
                        int(row["quantity"]),
                        row["source_ref"],
                        row["reconciliation_id"],
                    )
                )
    return events


def seed() -> None:
    initialize_database()
    with connect() as connection:
        connection.execute("DELETE FROM audit_events")
        connection.execute("DELETE FROM actions")
        connection.execute("DELETE FROM interview_notes")
        connection.execute("DELETE FROM timeline")
        connection.execute("DELETE FROM evidence")
        connection.execute("DELETE FROM cases")
        connection.execute("DELETE FROM events")
        events = load_synthetic_events()
        connection.executemany("INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?)", events)
        cases = [
            ("CASE-SYN-001", "receipt_mismatch", "scheduled reconciliation", "normal", "Synthetic receiving lead", "closed", "A receipt record shows 92 units against an expected 100. Verify documented operational explanations; no conclusion about intent is presumed.", "100 expected, 92 recorded: an eight-unit raw mismatch. A delayed correction explains five units and a documented damage adjustment explains three. The reconciliation is resolved; no theft or fraud finding is made.", 1, "SITE-NORTH", "receiving_handoff", "REC-SYN-001", "2026-10-19T10:15:00+00:00", "2026-10-22T14:00:00+00:00", "Resolved reconciliation issue: delayed correction record explains five units and documented damage adjustment explains three. Handoff process control recommended."),
            ("CASE-SYN-002", "receipt_mismatch", "scheduled reconciliation", "high", "Synthetic inventory analyst", "review", "A receipt record shows 10 units against an expected 12. The reason is not yet established; preserve uncertainty and seek source records.", "The synthetic records show 12 expected and 10 recorded. Two units remain unexplained; the reason is not established and no conclusion about intent is made. Request the correction log and handoff documentation before determining an outcome.", 1, "SITE-WEST", "returns_handoff", "REC-SYN-002", "2026-10-21T09:00:00+00:00", None, None),
        ]
        connection.executemany(
            """INSERT INTO cases
            (case_id, case_type, report_source, priority, owner, status, concern, report_summary, simulated,
             site_id, process_step, reconciliation_id, opened_at, closed_at, resolution)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            cases,
        )
        timeline = [
            ("TL-SYN-001", "CASE-SYN-001", "observation", "Initial receipt mismatch: 8 units", "Expected record contains 100 units; receipt record contains 92 units. This is a records discrepancy, not a theft conclusion.", "seed", "2026-10-19T09:10:00+00:00", "2026-10-19T10:15:00+00:00"),
            ("TL-SYN-002", "CASE-SYN-001", "observation", "Delayed correction located: 5 units", "A synthetic correction record posted the next day and accounts for five units.", "seed", "2026-10-20T11:30:00+00:00", "2026-10-20T12:00:00+00:00"),
            ("TL-SYN-003", "CASE-SYN-001", "observation", "Damage adjustment documented: 3 units", "A synthetic damage adjustment accounts for three units; the reconciliation is resolved.", "seed", "2026-10-19T10:00:00+00:00", "2026-10-20T12:05:00+00:00"),
            ("TL-SYN-004", "CASE-SYN-001", "reviewer_conclusion", "Resolved reconciliation issue", "The records difference is fully explained by a delayed correction and a documented damage adjustment. No theft finding is made.", "reviewer", "2026-10-22T14:00:00+00:00", "2026-10-22T14:00:00+00:00"),
            ("TL-SYN-005", "CASE-SYN-002", "observation", "Unresolved 2-unit mismatch", "Expected record contains 12 units; receipt record contains 10. Available synthetic records do not explain the difference.", "seed", "2026-10-21T08:00:00+00:00", "2026-10-21T09:00:00+00:00"),
            ("TL-SYN-006", "CASE-SYN-002", "hypothesis", "Potential record timing or handoff issue", "This is a testable possibility only, not a conclusion. Request the correction log and handoff documentation.", "analyst", None, "2026-10-21T09:05:00+00:00"),
        ]
        connection.executemany("INSERT INTO timeline VALUES (?, ?, ?, ?, ?, ?, ?, ?)", timeline)
        connection.execute(
            "INSERT INTO actions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("ACTION-SYN-001", "CASE-SYN-001", "Require a timestamped two-party handoff count and a linked correction reason before the receiving record is finalized.", "Synthetic receiving process owner", "2026-11-15", "open", None, "2026-10-22T14:00:00+00:00", None),
        )
        record_audit(connection, "seed", "seeded", "demo", "synthetic", {"events": len(events), "cases": len(cases)})
    print("Seeded synthetic cases CASE-SYN-001 and CASE-SYN-002")


if __name__ == "__main__":
    seed()