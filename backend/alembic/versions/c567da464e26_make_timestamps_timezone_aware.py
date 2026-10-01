"""Make timestamps timezone aware

Revision ID: c567da464e26
Revises: 2def9295d748
Create Date: 2026-10-01 10:14:12.064346

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'c567da464e26'
down_revision: Union[str, Sequence[str], None] = '2def9295d748'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # user
    op.alter_column('user', 'created_at', type_=sa.DateTime(timezone=True), existing_type=sa.DateTime())
    op.alter_column('user', 'updated_at', type_=sa.DateTime(timezone=True), existing_type=sa.DateTime())
    # service
    op.alter_column('service', 'created_at', type_=sa.DateTime(timezone=True), existing_type=sa.DateTime())
    op.alter_column('service', 'updated_at', type_=sa.DateTime(timezone=True), existing_type=sa.DateTime())
    # incident
    op.alter_column('incident', 'created_at', type_=sa.DateTime(timezone=True), existing_type=sa.DateTime())
    op.alter_column('incident', 'updated_at', type_=sa.DateTime(timezone=True), existing_type=sa.DateTime())
    op.alter_column('incident', 'resolved_at', type_=sa.DateTime(timezone=True), existing_type=sa.DateTime())
    # incidentupdate
    op.alter_column('incident_updates', 'created_at', type_=sa.DateTime(timezone=True), existing_type=sa.DateTime())
    # subscriber
    op.alter_column('subscriber', 'confirmation_token_expires_at', type_=sa.DateTime(timezone=True), existing_type=sa.DateTime())
    op.alter_column('subscriber', 'created_at', type_=sa.DateTime(timezone=True), existing_type=sa.DateTime())


def downgrade() -> None:
    """Downgrade schema."""
    # user
    op.alter_column('user', 'created_at', type_=sa.DateTime(), existing_type=sa.DateTime(timezone=True))
    op.alter_column('user', 'updated_at', type_=sa.DateTime(), existing_type=sa.DateTime(timezone=True))
    # service
    op.alter_column('service', 'created_at', type_=sa.DateTime(), existing_type=sa.DateTime(timezone=True))
    op.alter_column('service', 'updated_at', type_=sa.DateTime(), existing_type=sa.DateTime(timezone=True))
    # incident
    op.alter_column('incident', 'created_at', type_=sa.DateTime(), existing_type=sa.DateTime(timezone=True))
    op.alter_column('incident', 'updated_at', type_=sa.DateTime(), existing_type=sa.DateTime(timezone=True))
    op.alter_column('incident', 'resolved_at', type_=sa.DateTime(), existing_type=sa.DateTime(timezone=True))
    # incidentupdate
    op.alter_column('incident_updates', 'created_at', type_=sa.DateTime(), existing_type=sa.DateTime(timezone=True))
    # subscriber
    op.alter_column('subscriber', 'confirmation_token_expires_at', type_=sa.DateTime(), existing_type=sa.DateTime(timezone=True))
    op.alter_column('subscriber', 'created_at', type_=sa.DateTime(), existing_type=sa.DateTime(timezone=True))
