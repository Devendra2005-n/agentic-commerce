"""Append only triggers

Revision ID: a33c5b5c47b7
Revises: e922bf1c41ff
Create Date: 2026-08-24 15:58:30.613145

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a33c5b5c47b7'
down_revision: Union[str, Sequence[str], None] = 'e922bf1c41ff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add trigger function to reject UPDATE and DELETE
    op.execute("""
    CREATE OR REPLACE FUNCTION reject_mutation() RETURNS trigger AS $$
    BEGIN
      RAISE EXCEPTION '% is append-only; % is not permitted', TG_TABLE_NAME, TG_OP;
    END;
    $$ LANGUAGE plpgsql;
    """)

    # Attach trigger to intents
    op.execute("""
    DROP TRIGGER IF EXISTS trg_intents_append_only ON intents;
    CREATE TRIGGER trg_intents_append_only
      BEFORE UPDATE OR DELETE ON intents
      FOR EACH ROW EXECUTE FUNCTION reject_mutation();
    """)

    # Attach trigger to decisions
    op.execute("""
    DROP TRIGGER IF EXISTS trg_decisions_append_only ON decisions;
    CREATE TRIGGER trg_decisions_append_only
      BEFORE UPDATE OR DELETE ON decisions
      FOR EACH ROW EXECUTE FUNCTION reject_mutation();
    """)

    # Attach trigger to audit_events
    op.execute("""
    DROP TRIGGER IF EXISTS trg_audit_events_append_only ON audit_events;
    CREATE TRIGGER trg_audit_events_append_only
      BEFORE UPDATE OR DELETE ON audit_events
      FOR EACH ROW EXECUTE FUNCTION reject_mutation();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_audit_events_append_only ON audit_events;")
    op.execute("DROP TRIGGER IF EXISTS trg_decisions_append_only ON decisions;")
    op.execute("DROP TRIGGER IF EXISTS trg_intents_append_only ON intents;")
    op.execute("DROP FUNCTION IF EXISTS reject_mutation();")
