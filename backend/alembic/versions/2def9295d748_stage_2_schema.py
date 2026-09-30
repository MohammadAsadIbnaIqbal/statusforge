"""Stage_2_Schema

Revision ID: 2def9295d748
Revises: c57dde2d3f59
Create Date: 2026-09-28 13:25:13.258029

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '2def9295d748'
down_revision: Union[str, Sequence[str], None] = 'c57dde2d3f59'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create new tables
    op.create_table('incident',
    sa.Column('title', sqlmodel.sql.sqltypes.AutoString(length=200), nullable=False),
    sa.Column('status', sa.VARCHAR(length=20), nullable=False, server_default='INVESTIGATING'),
    sa.Column('impact', sa.VARCHAR(length=20), nullable=False),
    sa.CheckConstraint("status IN ('INVESTIGATING', 'IDENTIFIED', 'MONITORING', 'RESOLVED')", name='chk_incident_status'),
    sa.CheckConstraint("impact IN ('NONE', 'MINOR', 'MAJOR', 'CRITICAL')", name='chk_incident_impact'),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('owner_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('resolved_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['owner_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_incident_owner_id'), 'incident', ['owner_id'], unique=False)
    
    op.create_table('subscriber',
    sa.Column('email', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('owner_id', sa.Integer(), nullable=False),
    sa.Column('is_confirmed', sa.Boolean(), nullable=False, server_default='0'),
    sa.Column('confirmation_token', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True),
    sa.Column('confirmation_token_expires_at', sa.DateTime(), nullable=True),
    sa.Column('unsubscribe_token', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['owner_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('owner_id', 'email', name='uq_subscriber_owner_email')
    )
    op.create_index(op.f('ix_subscriber_confirmation_token'), 'subscriber', ['confirmation_token'], unique=True)
    op.create_index(op.f('ix_subscriber_owner_id'), 'subscriber', ['owner_id'], unique=False)
    op.create_index(op.f('ix_subscriber_unsubscribe_token'), 'subscriber', ['unsubscribe_token'], unique=True)
    
    op.create_table('incident_updates',
    sa.Column('status', sa.VARCHAR(length=20), nullable=False),
    sa.Column('message', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.CheckConstraint("status IN ('INVESTIGATING', 'IDENTIFIED', 'MONITORING', 'RESOLVED')", name='chk_incident_update_status'),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('incident_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['incident_id'], ['incident.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_incident_updates_incident_id'), 'incident_updates', ['incident_id'], unique=False)

    # 2. Add columns to 'user' as nullable
    op.add_column('user', sa.Column('organization_name', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True))
    op.add_column('user', sa.Column('organization_slug', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True))
    op.add_column('user', sa.Column('created_at', sa.DateTime(), nullable=True))
    op.add_column('user', sa.Column('updated_at', sa.DateTime(), nullable=True))

    # 3. Backfill data deterministically
    op.execute("UPDATE \"user\" SET organization_name = username || '''s Organization' WHERE organization_name IS NULL")
    op.execute("UPDATE \"user\" SET organization_slug = username || '-org' WHERE organization_slug IS NULL")
    op.execute("UPDATE \"user\" SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
    op.execute("UPDATE \"user\" SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL")
    op.execute("UPDATE \"user\" SET email = username || '@example.com' WHERE email IS NULL")

    # 4. Enforce NOT NULL constraints using batch mode
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column('organization_name', existing_type=sa.VARCHAR(length=100), nullable=False)
        batch_op.alter_column('organization_slug', existing_type=sa.VARCHAR(length=100), nullable=False)
        batch_op.alter_column('created_at', existing_type=sa.DateTime(), nullable=False)
        batch_op.alter_column('updated_at', existing_type=sa.DateTime(), nullable=False)
        batch_op.alter_column('email', existing_type=sa.VARCHAR(), nullable=False)
        batch_op.drop_index('ix_user_email')
        batch_op.create_index(batch_op.f('ix_user_email'), ['email'], unique=True)
        batch_op.create_index(batch_op.f('ix_user_organization_slug'), ['organization_slug'], unique=True)

    # 5. Rename product to service
    op.rename_table('product', 'service')

    # 6. Alter service table to match new model
    with op.batch_alter_table('service', schema=None) as batch_op:
        batch_op.add_column(sa.Column('description', sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True))
        batch_op.add_column(sa.Column('current_status', sa.VARCHAR(length=20), server_default='OPERATIONAL', nullable=False))
        batch_op.add_column(sa.Column('display_order', sa.Integer(), server_default='0', nullable=False))
        batch_op.add_column(sa.Column('is_visible', sa.Boolean(), server_default='1', nullable=False))
        batch_op.add_column(sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False))
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False))
        batch_op.drop_column('price')
        batch_op.drop_column('in_stock')
        batch_op.create_index(batch_op.f('ix_service_owner_id'), ['owner_id'], unique=False)
        batch_op.create_check_constraint('chk_service_status', "current_status IN ('OPERATIONAL', 'DEGRADED_PERFORMANCE', 'PARTIAL_OUTAGE', 'MAJOR_OUTAGE', 'UNDER_MAINTENANCE')")
        
    op.create_table('incident_services',
    sa.Column('incident_id', sa.Integer(), nullable=False),
    sa.Column('service_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['incident_id'], ['incident.id'], ),
    sa.ForeignKeyConstraint(['service_id'], ['service.id'], ),
    sa.PrimaryKeyConstraint('incident_id', 'service_id')
    )


def downgrade() -> None:
    pass
