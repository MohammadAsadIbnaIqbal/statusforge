"""multi_tenancy_security

Revision ID: 0b9388630e8b
Revises: 924a00eab92b
Create Date: 2026-10-04 09:45:42.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0b9388630e8b'
down_revision: Union[str, Sequence[str], None] = '924a00eab92b'
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
        'public.organization',
        'public.membership',
        'public.invitation'
    ]

    for table in tables:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"REVOKE ALL PRIVILEGES ON TABLE {table} FROM {grantees};")

def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != 'postgresql':
        return

    raise NotImplementedError("Downgrade is intentionally unsupported for security hardening.")
