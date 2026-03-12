"""add campaign start_date and end_date columns

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-03-11 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c2d3e4f5a6b7"
down_revision = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("campaigns", sa.Column("start_date", sa.DateTime(), nullable=True))
    op.add_column("campaigns", sa.Column("end_date", sa.DateTime(), nullable=True))
    op.create_check_constraint(
        "ck_campaign_date_window",
        "campaigns",
        "end_date IS NULL OR start_date IS NULL OR end_date >= start_date",
    )


def downgrade() -> None:
    op.drop_constraint("ck_campaign_date_window", "campaigns", type_="check")
    op.drop_column("campaigns", "end_date")
    op.drop_column("campaigns", "start_date")

