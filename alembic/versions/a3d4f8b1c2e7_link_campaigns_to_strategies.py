"""link campaigns to strategies

Revision ID: a3d4f8b1c2e7
Revises: 9e226f34648f
Create Date: 2026-02-25 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a3d4f8b1c2e7"
down_revision = "9e226f34648f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("campaigns", sa.Column("strategy_id", sa.String(), nullable=True))
    op.add_column("campaigns", sa.Column("strategy_version_no", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_campaigns_strategy_id_strategies",
        "campaigns",
        "strategies",
        ["strategy_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_campaigns_org_strategy", "campaigns", ["organization_id", "strategy_id"], unique=False)
    op.create_index(
        "ix_campaigns_org_strategy_version",
        "campaigns",
        ["organization_id", "strategy_id", "strategy_version_no"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_campaigns_org_strategy_version", table_name="campaigns")
    op.drop_index("ix_campaigns_org_strategy", table_name="campaigns")
    op.drop_constraint("fk_campaigns_strategy_id_strategies", "campaigns", type_="foreignkey")
    op.drop_column("campaigns", "strategy_version_no")
    op.drop_column("campaigns", "strategy_id")
