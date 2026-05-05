"""Add user documents table

Revision ID: 20260502_add_user_documents
Revises: 20260502_add_consent_timestamp
Create Date: 2026-05-02 00:00:01.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260502_add_user_documents"
down_revision: Union[str, None] = "20260502_add_consent_timestamp"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_documents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("document_type", sa.String(length=40), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=True),
        sa.Column("extracted_text", sa.Text(), nullable=False),
        sa.Column("extracted_signals", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_documents_created_at"), "user_documents", ["created_at"], unique=False)
    op.create_index(op.f("ix_user_documents_user_id"), "user_documents", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_user_documents_user_id"), table_name="user_documents")
    op.drop_index(op.f("ix_user_documents_created_at"), table_name="user_documents")
    op.drop_table("user_documents")
