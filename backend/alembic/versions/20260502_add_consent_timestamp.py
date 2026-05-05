"""Add consent timestamp to users

Revision ID: 20260502_add_consent_timestamp
Revises: bb66ab61496b
Create Date: 2026-05-02 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260502_add_consent_timestamp"
down_revision: Union[str, None] = "bb66ab61496b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("consent_given_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "consent_given_at")
