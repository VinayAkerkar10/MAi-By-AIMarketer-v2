"""merge mailrelay migration heads

Revision ID: 26c19ca8e99d
Revises: 95cbf5ceaefc, e1f2a3b4c5d6
Create Date: 2026-04-07 11:44:06.718551
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '26c19ca8e99d'
down_revision = ('95cbf5ceaefc', 'e1f2a3b4c5d6')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass