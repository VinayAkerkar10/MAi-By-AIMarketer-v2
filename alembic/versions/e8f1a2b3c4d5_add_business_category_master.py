"""add business category master

Revision ID: e8f1a2b3c4d5
Revises: c1f2d3e4a5b6
Create Date: 2026-03-10 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e8f1a2b3c4d5"
down_revision = "c1f2d3e4a5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "business_category_master",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("category_name", sa.String(), nullable=False, unique=True),
        sa.Column("parent_category", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_business_category_master_id",
        "business_category_master",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_business_category_master_category_name",
        "business_category_master",
        ["category_name"],
        unique=True,
    )
    op.create_index(
        "ix_business_category_master_parent_category",
        "business_category_master",
        ["parent_category"],
        unique=False,
    )

    category_table = sa.table(
        "business_category_master",
        sa.column("category_name", sa.String()),
        sa.column("parent_category", sa.String()),
    )
    op.bulk_insert(
        category_table,
        [
            {"category_name": "Technology", "parent_category": "B2B Services"},
            {"category_name": "Healthcare", "parent_category": "B2B Services"},
            {"category_name": "Finance", "parent_category": "B2B Services"},
            {"category_name": "Manufacturing", "parent_category": "Industry"},
            {"category_name": "Professional Services", "parent_category": "B2B Services"},
            {"category_name": "Retail", "parent_category": "Commerce"},
            {"category_name": "Education", "parent_category": "Services"},
            {"category_name": "Software Development", "parent_category": "Technology"},
            {"category_name": "Data Analytics", "parent_category": "Technology"},
            {"category_name": "Cloud Services", "parent_category": "Technology"},
            {"category_name": "Cybersecurity", "parent_category": "Technology"},
            {"category_name": "Artificial Intelligence", "parent_category": "Technology"},
            {"category_name": "Consulting", "parent_category": "Professional Services"},
            {"category_name": "Marketing Agency", "parent_category": "Professional Services"},
        ],
    )

    op.alter_column(
        "business_category_master",
        "created_at",
        server_default=None,
        existing_type=sa.DateTime(),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_business_category_master_parent_category",
        table_name="business_category_master",
    )
    op.drop_index(
        "ix_business_category_master_category_name",
        table_name="business_category_master",
    )
    op.drop_index(
        "ix_business_category_master_id",
        table_name="business_category_master",
    )
    op.drop_table("business_category_master")
