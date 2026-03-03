"""Initial migration - create all tables.

Revision ID: 001_initial
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('telegram_id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.String(255), nullable=True),
        sa.Column('first_name', sa.String(255), nullable=True),
        sa.Column('last_name', sa.String(255), nullable=True),
        sa.Column('role', sa.Enum('admin', 'user', name='user_role'), nullable=False, server_default='user'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('telegram_id')
    )
    op.create_index('ix_users_telegram_id', 'users', ['telegram_id'], unique=True)

    # Create deposits table
    op.create_table(
        'deposits',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('bot_token', sa.String(255), nullable=True),
        sa.Column('group_chat_id', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('bot_token')
    )
    op.create_index('ix_deposits_name', 'deposits', ['name'], unique=True)

    # Create sites table
    op.create_table(
        'sites',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('deposit_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('inj_well_name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['deposit_id'], ['deposits.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('deposit_id', 'name', name='uq_site_deposit_name')
    )
    op.create_index('ix_sites_name', 'sites', ['name'], unique=False)
    op.create_index('ix_sites_deposit_id', 'sites', ['deposit_id'], unique=False)

    # Create wells table
    op.create_table(
        'wells',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('site_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('well_type', sa.Enum('injection', 'production', 'gryphon', name='well_type'), nullable=False),
        sa.Column('lat', sa.Float(), nullable=True),
        sa.Column('lon', sa.Float(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['sites.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('site_id', 'name', name='uq_well_site_name')
    )
    op.create_index('ix_wells_site_id', 'wells', ['site_id'], unique=False)
    op.create_index('ix_wells_site_name', 'wells', ['site_id', 'name'], unique=False)

    # Create sampling_events table
    op.create_table(
        'sampling_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('site_id', sa.Integer(), nullable=False),
        sa.Column('well_id', sa.Integer(), nullable=False),
        sa.Column('operator_user_id', sa.Integer(), nullable=False),
        sa.Column('well_status', sa.Enum('working', 'repair', 'not_working', 'krs', name='well_status'), nullable=False),
        sa.Column('sampling_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sampling_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sample_type', sa.Enum('water', 'oil', 'gas', 'not_sampled_gas', 'other', name='sample_type'), nullable=False),
        sa.Column('sample_note', sa.Text(), nullable=True),
        sa.Column('volume_liters', sa.Float(), nullable=False, server_default='0'),
        sa.Column('gps_status', sa.Enum('received', 'timeout', 'skipped_by_user', name='gps_status'), nullable=False),
        sa.Column('lat', sa.Float(), nullable=True),
        sa.Column('lon', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['sites.id'], ),
        sa.ForeignKeyConstraint(['well_id'], ['wells.id'], ),
        sa.ForeignKeyConstraint(['operator_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_sampling_events_site_id', 'sampling_events', ['site_id'], unique=False)
    op.create_index('ix_sampling_events_well_id', 'sampling_events', ['well_id'], unique=False)
    op.create_index('ix_sampling_events_operator_user_id', 'sampling_events', ['operator_user_id'], unique=False)
    op.create_index('ix_sampling_events_site_well_created', 'sampling_events', ['site_id', 'well_id', 'created_at'], unique=False)
    op.create_index('ix_sampling_events_operator_created', 'sampling_events', ['operator_user_id', 'created_at'], unique=False)


def downgrade() -> None:
    op.drop_table('sampling_events')
    op.drop_table('wells')
    op.drop_table('sites')
    op.drop_table('deposits')
    op.drop_table('users')

    sa.Enum(name='user_role').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='well_type').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='well_status').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='gps_status').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='sample_type').drop(op.get_bind(), checkfirst=True)
