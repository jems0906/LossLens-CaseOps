from pathlib import Path

from fastapi.testclient import TestClient

from app import db
from app import config
from app.main import app
from app.services.reconciliation import calculate_reconciliation


ANALYST = {"Authorization": "Bearer local-demo-analyst"}
REVIEWER = {"Authorization": "Bearer local-demo-reviewer"}


def test_production_configuration_rejects_placeholder_credentials(monkeypatch) -> None:
    monkeypatch.setattr(config, "ENVIRONMENT", "production")
    monkeypatch.setattr(config, "ANALYST_TOKEN", "replace-with-a-long-random-analyst-token")
    monkeypatch.setattr(config, "REVIEWER_TOKEN", "replace-with-a-different-long-random-reviewer-token")
    try:
        config.validate_configuration()
    except RuntimeError as error:
        assert "at least 32 characters" in str(error)
    else:
        raise AssertionError("Production accepted placeholder credentials")


def test_production_configuration_accepts_distinct_long_credentials(monkeypatch) -> None:
    monkeypatch.setattr(config, "ENVIRONMENT", "production")
    monkeypatch.setattr(config, "ANALYST_TOKEN", "a" * 40)
    monkeypatch.setattr(config, "REVIEWER_TOKEN", "b" * 40)
    config.validate_configuration()


def test_reconciliation_separates_raw_explained_and_unknown_units() -> None:
    result = calculate_reconciliation(
        [
            {"event_type": "shipment", "quantity": 100},
            {"event_type": "receipt", "quantity": 92},
            {"event_type": "receipt_correction", "quantity": 5},
            {"event_type": "damage_adjustment", "quantity": 3},
        ]
    )
    assert result["raw_discrepancy_units"] == 8
    assert result["confirmed_recording_error_units"] == 5
    assert result["documented_adjustment_units"] == 3
    assert result["unexplained_units"] == 0
    assert result["classification"] == "resolved_reconciliation_issue"


def test_reconciliation_reports_overages_as_variances() -> None:
    result = calculate_reconciliation(
        [
            {"event_type": "shipment", "quantity": 8},
            {"event_type": "receipt", "quantity": 10},
            {"event_type": "damage_adjustment", "quantity": 2},
        ]
    )
    assert result["raw_discrepancy_units"] == 2
    assert result["unexplained_units"] == 2
    assert result["classification"] == "unexplained_discrepancy"


def test_import_rejects_duplicate_ids_and_timezone_free_timestamps(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    with TestClient(app) as client:
        content = (
            "event_id,event_type,process_step,site_id,occurred_at,quantity,source_ref,reconciliation_id\n"
            "DUP,shipment,receiving,SITE-TEST,2026-10-01T10:00:00,4,DOC-1,REC-1\n"
            "DUP,receipt,receiving,SITE-TEST,2026-10-01T10:00:00Z,3,DOC-2,REC-1\n"
        )
        response = client.post(
            "/api/imports/events",
            headers=ANALYST,
            files={"file": ("events.csv", content, "text/csv")},
        )
        assert response.status_code == 422
        assert response.json()["detail"]["message"] == "No rows imported"
        assert not db.connect().execute("SELECT 1 FROM events").fetchone()


def test_import_accepts_all_synthetic_event_fixtures_once(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "all-events.db")
    fixture_dir = Path(__file__).resolve().parents[2] / "fixtures"
    contents = []
    for filename in (
        "synthetic_inventory_events.csv",
        "synthetic_transfer_events.csv",
        "synthetic_return_events.csv",
        "synthetic_adjustment_events.csv",
    ):
        contents.extend((fixture_dir / filename).read_text(encoding="utf-8").splitlines()[1:])
    csv_content = (
        "event_id,event_type,process_step,site_id,occurred_at,quantity,source_ref,reconciliation_id\n"
        + "\n".join(contents)
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/imports/events",
            headers=ANALYST,
            files={"file": ("synthetic-events.csv", csv_content, "text/csv")},
        )
        assert response.status_code == 200
        assert response.json()["imported"] == 13
        duplicate = client.post(
            "/api/imports/events",
            headers=ANALYST,
            files={"file": ("synthetic-events.csv", csv_content, "text/csv")},
        )
        assert duplicate.status_code == 422
        assert client.get("/api/reports/leadership", headers=ANALYST).status_code == 200


def test_reviewer_permission_required_and_case_must_follow_review_states(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "workflow.db")
    with TestClient(app) as client:
        created = client.post(
            "/api/cases",
            headers=ANALYST,
            json={
                "case_id": "CASE-TEST-1",
                "case_type": "receipt_mismatch",
                "report_source": "synthetic test",
                "priority": "normal",
                "owner": "Synthetic analyst",
                "concern": "Two synthetic records differ; cause is unknown.",
                "site_id": "SITE-TEST",
                "process_step": "receiving_handoff",
                "reconciliation_id": "REC-TEST",
            },
        )
        assert created.status_code == 201
        invalid_timeline = client.post(
            "/api/cases/CASE-TEST-1/timeline",
            headers=ANALYST,
            json={
                "category": "observation",
                "summary": "Synthetic timestamp check",
                "details": "This row has a timezone-free event time.",
                "event_time": "2026-10-29T10:00:00",
            },
        )
        assert invalid_timeline.status_code == 422
        assert client.post("/api/cases/CASE-TEST-1/reviews/approve", headers=ANALYST).status_code == 403
        assert client.post("/api/cases/CASE-TEST-1/reviews/submit", headers=ANALYST).json()["status"] == "review"
        assert client.post("/api/cases/CASE-TEST-1/reviews/approve", headers=REVIEWER).status_code == 409
        report_update = client.patch(
            "/api/cases/CASE-TEST-1",
            headers=ANALYST,
            json={"report_summary": "The synthetic records differ; the cause remains unestablished."},
        )
        assert report_update.status_code == 200
        cleared_report = client.patch(
            "/api/cases/CASE-TEST-1",
            headers=ANALYST,
            json={"report_summary": None},
        )
        assert cleared_report.status_code == 400
        assert client.get("/api/cases/CASE-TEST-1", headers=ANALYST).json()["report_summary"] == report_update.json()["report_summary"]
        assert client.post("/api/cases/CASE-TEST-1/reviews/approve", headers=REVIEWER).json()["status"] == "approved_report"
        closed = client.post(
            "/api/cases/CASE-TEST-1/reviews/close",
            headers=REVIEWER,
            json={"resolution": "Records reviewed; the cause remains unestablished."},
        )
        assert closed.status_code == 200
        assert closed.json()["status"] == "closed"
        edit_closed = client.patch(
            "/api/cases/CASE-TEST-1",
            headers=ANALYST,
            json={"report_summary": "A later change should not overwrite the approved report."},
        )
        assert edit_closed.status_code == 409


def test_evidence_access_and_metadata_changes_are_audited(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "evidence.db")
    with TestClient(app) as client:
        client.post(
            "/api/cases",
            headers=ANALYST,
            json={
                "case_id": "CASE-EVIDENCE-1",
                "case_type": "receipt_mismatch",
                "report_source": "synthetic test",
                "priority": "normal",
                "owner": "Synthetic analyst",
                "concern": "Two synthetic records differ; cause is unknown.",
                "site_id": "SITE-TEST",
                "process_step": "receiving_handoff",
                "simulated": True,
            },
        )
        evidence = client.post(
            "/api/cases/CASE-EVIDENCE-1/evidence",
            headers=ANALYST,
            json={
                "source_ref": "DOC-SYN-1",
                "collector": "Synthetic analyst",
                "collection_time": "2026-10-29T10:00:00Z",
                "notes": "Initial synthetic reference",
            },
        )
        assert evidence.status_code == 201
        evidence_id = evidence.json()["evidence_id"]
        assert client.get("/api/cases/CASE-EVIDENCE-1/evidence", headers=ANALYST).status_code == 200
        assert client.patch(
            f"/api/cases/CASE-EVIDENCE-1/evidence/{evidence_id}",
            headers=ANALYST,
            json={"notes": "Updated synthetic reference note"},
        ).status_code == 200
        assert client.patch(
            f"/api/cases/CASE-EVIDENCE-1/evidence/{evidence_id}",
            headers=ANALYST,
            json={"collector": None},
        ).status_code == 422
        with db.connect() as connection:
            audit_rows = connection.execute(
                "SELECT actor, action FROM audit_events WHERE entity IN ('evidence', 'evidence_register')"
            ).fetchall()
        assert {tuple(row) for row in audit_rows} == {
            ("synthetic-analyst", "created"),
            ("synthetic-analyst", "accessed"),
            ("synthetic-analyst", "updated_metadata"),
        }