"""task reminders and reminder preferences

Revision ID: d2b3c4e5f6a7
Revises: c1a2b3d4e5f6
Create Date: 2026-11-23 16:30:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "d2b3c4e5f6a7"
down_revision = "c1a2b3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("plan_activities", schema=None) as batch_op:
        batch_op.add_column(sa.Column("reminder_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.add_column(sa.Column("remind_days_before", sa.Integer(), nullable=True))

    op.create_table(
        "reminder_preferences",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("lead_days", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_reminder_preferences")),
    )


def downgrade() -> None:
    op.drop_table("reminder_preferences")
    with op.batch_alter_table("plan_activities", schema=None) as batch_op:
        batch_op.drop_column("remind_days_before")
        batch_op.drop_column("reminder_enabled")
