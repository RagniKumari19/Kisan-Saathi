"""crop calendar and season planner

Revision ID: c1a2b3d4e5f6
Revises: 308227c90246
Create Date: 2026-11-23 15:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "c1a2b3d4e5f6"
down_revision = "308227c90246"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "crop_plans",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("farm_id", sa.String(length=36), nullable=False),
        sa.Column("crop_slug", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=True),
        sa.Column("sowing_date", sa.Date(), nullable=False),
        sa.Column("expected_harvest_date", sa.Date(), nullable=True),
        sa.Column("farming_method", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("current_stage", sa.String(length=24), nullable=False),
        sa.Column("progress_pct", sa.Float(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["farm_id"], ["farms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_crop_plans")),
    )
    with op.batch_alter_table("crop_plans", schema=None) as batch_op:
        batch_op.create_index("ix_crop_plans_user_created", ["user_id", "created_at"], unique=False)

    op.create_table(
        "plan_activities",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("plan_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("stage", sa.String(length=24), nullable=False),
        sa.Column("activity_type", sa.String(length=24), nullable=False),
        sa.Column("title_en", sa.String(length=160), nullable=False),
        sa.Column("title_hi", sa.String(length=160), nullable=False),
        sa.Column("detail_en", sa.Text(), nullable=False),
        sa.Column("detail_hi", sa.Text(), nullable=False),
        sa.Column("materials", sa.JSON(), nullable=False),
        sa.Column("importance", sa.String(length=12), nullable=False),
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column("weather_sensitive", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("rescheduled_from", sa.Date(), nullable=True),
        sa.Column("is_custom", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["crop_plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_plan_activities")),
    )
    with op.batch_alter_table("plan_activities", schema=None) as batch_op:
        batch_op.create_index("ix_plan_activities_plan_date", ["plan_id", "scheduled_date"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("plan_activities", schema=None) as batch_op:
        batch_op.drop_index("ix_plan_activities_plan_date")
    op.drop_table("plan_activities")
    with op.batch_alter_table("crop_plans", schema=None) as batch_op:
        batch_op.drop_index("ix_crop_plans_user_created")
    op.drop_table("crop_plans")
