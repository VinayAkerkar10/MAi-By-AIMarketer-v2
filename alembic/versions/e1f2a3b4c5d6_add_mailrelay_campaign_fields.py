"""add mailrelay campaign fields

Revision ID: e1f2a3b4c5d6
Revises: b1c2d3e4f5a6
Create Date: 2026-04-07 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "e1f2a3b4c5d6"
down_revision = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("campaigns", sa.Column("scheduled_at", sa.DateTime(), nullable=True))
    op.add_column("campaigns", sa.Column("email_provider", sa.String(), nullable=True))
    op.add_column("campaigns", sa.Column("last_error", sa.Text(), nullable=True))
    op.add_column("campaigns", sa.Column("last_attempt_at", sa.DateTime(), nullable=True))
    op.add_column("campaigns", sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"))
    op.execute("UPDATE campaigns SET scheduled_at = schedule_date WHERE scheduled_at IS NULL AND schedule_date IS NOT NULL")
    op.alter_column("campaigns", "retry_count", server_default=None)

    op.drop_constraint("ck_campaign_status", "campaigns", type_="check")
    op.create_check_constraint(
        "ck_campaign_status",
        "campaigns",
        "status IN ('draft','pending','scheduled','sending','active','paused','stopped','sent','failed','completed')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_campaign_status", "campaigns", type_="check")
    op.create_check_constraint(
        "ck_campaign_status",
        "campaigns",
        "status IN ('draft','scheduled','active','paused','stopped','failed','completed')",
    )

    op.drop_column("campaigns", "retry_count")
    op.drop_column("campaigns", "last_attempt_at")
    op.drop_column("campaigns", "last_error")
    op.drop_column("campaigns", "email_provider")
    op.drop_column("campaigns", "scheduled_at")
