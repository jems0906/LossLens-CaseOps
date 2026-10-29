"""Create the initial synthetic case workspace schema."""

from alembic import op

from app.db import SCHEMA


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    for statement in SCHEMA.split(";"):
        if statement.strip():
            connection.exec_driver_sql(statement)


def downgrade() -> None:
    for table in ("audit_events", "actions", "interview_notes", "timeline", "evidence", "cases", "events"):
        op.execute(f"DROP TABLE IF EXISTS {table}")