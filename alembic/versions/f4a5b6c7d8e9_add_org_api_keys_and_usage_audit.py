"""add organization api keys and api usage audit logs

Revision ID: f4a5b6c7d8e9
Revises: e8f1a2b3c4d5
Create Date: 2026-03-10 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f4a5b6c7d8e9"
down_revision = "e8f1a2b3c4d5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organization_api_keys",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("provider_name", sa.String(), nullable=False),
        sa.Column("api_key", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "provider_name", name="uq_org_provider_api_key"),
        sa.CheckConstraint("status IN ('active','disabled')", name="ck_org_api_key_status"),
    )
    op.create_index("ix_organization_api_keys_id", "organization_api_keys", ["id"], unique=False)
    op.create_index("ix_organization_api_keys_organization_id", "organization_api_keys", ["organization_id"], unique=False)
    op.create_index("ix_organization_api_keys_provider_name", "organization_api_keys", ["provider_name"], unique=False)
    op.create_index("ix_org_api_keys_org_provider", "organization_api_keys", ["organization_id", "provider_name"], unique=False)

    op.create_table(
        "api_usage_audit_logs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("provider_name", sa.String(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("duration", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("duration >= 0", name="ck_api_usage_duration_non_negative"),
    )
    op.create_index("ix_api_usage_audit_logs_id", "api_usage_audit_logs", ["id"], unique=False)
    op.create_index("ix_api_usage_audit_logs_organization_id", "api_usage_audit_logs", ["organization_id"], unique=False)
    op.create_index("ix_api_usage_audit_logs_provider_name", "api_usage_audit_logs", ["provider_name"], unique=False)
    op.create_index("ix_api_usage_audit_logs_timestamp", "api_usage_audit_logs", ["timestamp"], unique=False)
    op.create_index("ix_api_usage_audit_logs_user_id", "api_usage_audit_logs", ["user_id"], unique=False)
    op.create_index("ix_api_usage_org_time", "api_usage_audit_logs", ["organization_id", "timestamp"], unique=False)
    op.create_index("ix_api_usage_org_provider", "api_usage_audit_logs", ["organization_id", "provider_name"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_api_usage_org_provider", table_name="api_usage_audit_logs")
    op.drop_index("ix_api_usage_org_time", table_name="api_usage_audit_logs")
    op.drop_index("ix_api_usage_audit_logs_user_id", table_name="api_usage_audit_logs")
    op.drop_index("ix_api_usage_audit_logs_timestamp", table_name="api_usage_audit_logs")
    op.drop_index("ix_api_usage_audit_logs_provider_name", table_name="api_usage_audit_logs")
    op.drop_index("ix_api_usage_audit_logs_organization_id", table_name="api_usage_audit_logs")
    op.drop_index("ix_api_usage_audit_logs_id", table_name="api_usage_audit_logs")
    op.drop_table("api_usage_audit_logs")

    op.drop_index("ix_org_api_keys_org_provider", table_name="organization_api_keys")
    op.drop_index("ix_organization_api_keys_provider_name", table_name="organization_api_keys")
    op.drop_index("ix_organization_api_keys_organization_id", table_name="organization_api_keys")
    op.drop_index("ix_organization_api_keys_id", table_name="organization_api_keys")
    op.drop_table("organization_api_keys")
