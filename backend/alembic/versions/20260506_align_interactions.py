"""Align interactions with conversations

Revision ID: 20260506_align_interactions_conversations
Revises: 20260505_add_conversations
Create Date: 2026-05-06 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260506_align_interactions"
down_revision: Union[str, None] = "20260505_add_conversations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    interaction_columns = {column["name"] for column in inspector.get_columns("interactions")}
    interaction_indexes = {index["name"] for index in inspector.get_indexes("interactions")}

    if "session_id" in interaction_columns and "conversation_id" not in interaction_columns:
        bind.execute(
            sa.text(
                """
                INSERT INTO conversations (id, user_id, title, created_at, updated_at)
                SELECT
                    session_id,
                    user_id,
                    'Imported chat',
                    MIN(created_at),
                    MAX(created_at)
                FROM interactions
                GROUP BY session_id, user_id
                ON CONFLICT (id) DO NOTHING
                """
            )
        )

        if "ix_interactions_session_id" in interaction_indexes:
            op.drop_index("ix_interactions_session_id", table_name="interactions")

        op.alter_column("interactions", "session_id", new_column_name="conversation_id")
        op.create_index(op.f("ix_interactions_conversation_id"), "interactions", ["conversation_id"], unique=False)

    if "memory_type" not in interaction_columns:
        op.add_column("interactions", sa.Column("memory_type", sa.String(length=50), nullable=True))
        op.execute("UPDATE interactions SET memory_type = 'short_term' WHERE memory_type IS NULL")
        op.alter_column("interactions", "memory_type", nullable=True, server_default=None)

    inspector = sa.inspect(bind)
    interaction_fks = {fk["name"] for fk in inspector.get_foreign_keys("interactions") if fk["name"]}
    interaction_columns = {column["name"] for column in inspector.get_columns("interactions")}
    if (
        "conversation_id" in interaction_columns
        and "fk_interactions_conversation_id_conversations" not in interaction_fks
    ):
        op.create_foreign_key(
            "fk_interactions_conversation_id_conversations",
            "interactions",
            "conversations",
            ["conversation_id"],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    interaction_columns = {column["name"] for column in inspector.get_columns("interactions")}
    interaction_indexes = {index["name"] for index in inspector.get_indexes("interactions")}
    interaction_fks = {fk["name"] for fk in inspector.get_foreign_keys("interactions") if fk["name"]}

    if "fk_interactions_conversation_id_conversations" in interaction_fks:
        op.drop_constraint("fk_interactions_conversation_id_conversations", "interactions", type_="foreignkey")

    if "memory_type" in interaction_columns:
        op.drop_column("interactions", "memory_type")

    if "conversation_id" in interaction_columns and "session_id" not in interaction_columns:
        if "ix_interactions_conversation_id" in interaction_indexes:
            op.drop_index("ix_interactions_conversation_id", table_name="interactions")
        op.alter_column("interactions", "conversation_id", new_column_name="session_id")
        op.create_index(op.f("ix_interactions_session_id"), "interactions", ["session_id"], unique=False)
