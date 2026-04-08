"""make campaign datetimes timezone aware

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-04-08 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "f2a3b4c5d6e7"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for column_name in (
        "schedule_date",
        "scheduled_at",
        "start_date",
        "end_date",
        "created_at",
        "updated_at",
        "deployed_at",
        "last_attempt_at",
    ):
        op.alter_column(
            "campaigns",
            column_name,
            existing_type=sa.DateTime(),
            type_=sa.DateTime(timezone=True),
            postgresql_using=f"{column_name} AT TIME ZONE 'UTC'",
            existing_nullable=True,
        )


def downgrade() -> None:
    for column_name in (
        "schedule_date",
        "scheduled_at",
        "start_date",
        "end_date",
        "created_at",
        "updated_at",
        "deployed_at",
        "last_attempt_at",
    ):
        op.alter_column(
            "campaigns",
            column_name,
            existing_type=sa.DateTime(timezone=True),
            type_=sa.DateTime(),
            postgresql_using=f"{column_name} AT TIME ZONE 'UTC'",
            existing_nullable=True,
        )
