"""Supabase DB security

Revision ID: d1f8a7e93000
Revises: c567da464e26
Create Date: 2026-10-03 16:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd1f8a7e93000'
down_revision: Union[str, Sequence[str], None] = 'c567da464e26'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != 'postgresql':
        return

    # Supabase provides the anon/authenticated roles; plain PostgreSQL (local Docker, CI) does not.
    # Only revoke from roles that exist so the migration runs on both. PUBLIC always exists.
    found = {row[0] for row in conn.execute(sa.text("SELECT rolname FROM pg_roles WHERE rolname IN ('anon', 'authenticated')"))}
    grantees = ", ".join([r for r in ("anon", "authenticated") if r in found] + ["PUBLIC"])

    tables = [
        'public."user"',
        'public.service',
        'public.incident',
        'public.incident_updates',
        'public.incident_services',
        'public.subscriber'
    ]

    for table in tables:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"REVOKE ALL PRIVILEGES ON TABLE {table} FROM {grantees};")

    op.execute(f"ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public REVOKE ALL ON TABLES FROM {grantees};")
    op.execute(f"ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public REVOKE ALL ON SEQUENCES FROM {grantees};")
    op.execute(f"ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public REVOKE ALL ON FUNCTIONS FROM {grantees};")

def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != 'postgresql':
        return

    raise NotImplementedError(
        "Downgrade is intentionally unsupported. "
        "Reverting security hardening requires manual review to prevent accidentally granting broad privileges."
    )
