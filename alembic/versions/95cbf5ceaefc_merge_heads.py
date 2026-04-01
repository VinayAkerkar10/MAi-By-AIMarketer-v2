"""merge heads

Revision ID: 95cbf5ceaefc
Revises: cd8180691924, a9b8c7d6e5f4
Create Date: 2026-04-01 07:09:02.164484
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '95cbf5ceaefc'
down_revision = ('cd8180691924', 'a9b8c7d6e5f4')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass