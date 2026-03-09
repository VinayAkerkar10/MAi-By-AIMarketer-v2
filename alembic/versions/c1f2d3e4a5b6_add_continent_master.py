"""add continent master

Revision ID: c1f2d3e4a5b6
Revises: b7c9d3e4f1a2
Create Date: 2026-03-09 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c1f2d3e4a5b6"
down_revision = "b7c9d3e4f1a2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "continent_master",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False, unique=True),
    )
    op.create_index("ix_continent_master_id", "continent_master", ["id"], unique=False)
    op.create_index("ix_continent_master_name", "continent_master", ["name"], unique=True)

    continent_table = sa.table(
        "continent_master",
        sa.column("name", sa.String()),
    )
    op.bulk_insert(
        continent_table,
        [
            {"name": "Asia"},
            {"name": "Africa"},
            {"name": "Europe"},
            {"name": "MENA"},
            {"name": "North America"},
            {"name": "South America"},
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_continent_master_name", table_name="continent_master")
    op.drop_index("ix_continent_master_id", table_name="continent_master")
    op.drop_table("continent_master")
