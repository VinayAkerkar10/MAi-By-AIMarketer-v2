"""add browser extension source and audit fields

Revision ID: a9b8c7d6e5f4
Revises: f4a5b6c7d8e9
Create Date: 2026-03-25 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a9b8c7d6e5f4"
down_revision: Union[str, Sequence[str], None] = "f4a5b6c7d8e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE leadsource ADD VALUE IF NOT EXISTS 'BROWSER_EXTENSION'")

    op.add_column("api_usage_audit_logs", sa.Column("task_id", sa.String(), nullable=True))
    op.add_column("api_usage_audit_logs", sa.Column("success", sa.Boolean(), nullable=True))
    op.add_column("api_usage_audit_logs", sa.Column("error_message", sa.Text(), nullable=True))
    op.add_column("api_usage_audit_logs", sa.Column("lead_count", sa.Integer(), nullable=False, server_default="0"))
    op.create_index("ix_api_usage_audit_logs_task_id", "api_usage_audit_logs", ["task_id"], unique=False)
    op.create_foreign_key(
        "fk_api_usage_audit_logs_task_id",
        "api_usage_audit_logs",
        "lead_scrape_tasks",
        ["task_id"],
        ["id"],
    )
    op.create_check_constraint(
        "ck_api_usage_lead_count_non_negative",
        "api_usage_audit_logs",
        "lead_count >= 0",
    )
    op.alter_column("api_usage_audit_logs", "lead_count", server_default=None)


def downgrade() -> None:
    op.drop_constraint("ck_api_usage_lead_count_non_negative", "api_usage_audit_logs", type_="check")
    op.drop_constraint("fk_api_usage_audit_logs_task_id", "api_usage_audit_logs", type_="foreignkey")
    op.drop_index("ix_api_usage_audit_logs_task_id", table_name="api_usage_audit_logs")
    op.drop_column("api_usage_audit_logs", "lead_count")
    op.drop_column("api_usage_audit_logs", "error_message")
    op.drop_column("api_usage_audit_logs", "success")
    op.drop_column("api_usage_audit_logs", "task_id")
    # PostgreSQL enum values are intentionally left in place during downgrade.
