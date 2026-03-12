"""add stopped to campaign status constraint

Revision ID: b1c2d3e4f5a6
Revises: f4a5b6c7d8e9
Create Date: 2026-03-11 00:00:00.000000
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "b1c2d3e4f5a6"
down_revision = "f4a5b6c7d8e9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_campaign_status", "campaigns", type_="check")
    op.create_check_constraint(
        "ck_campaign_status",
        "campaigns",
        "status IN ('draft','scheduled','active','paused','stopped','failed','completed')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_campaign_status", "campaigns", type_="check")
    op.create_check_constraint(
        "ck_campaign_status",
        "campaigns",
        "status IN ('draft','scheduled','active','paused','failed','completed')",
    )
