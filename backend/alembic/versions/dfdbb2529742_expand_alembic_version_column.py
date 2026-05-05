from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'your_generated_id'
down_revision = '20260505_add_conversations'  # or your latest BEFORE failing one
branch_labels = None
depends_on = None

def upgrade():
    op.alter_column(
        "alembic_version",
        "version_num",
        type_=sa.String(100)
    )

def downgrade():
    op.alter_column(
        "alembic_version",
        "version_num",
        type_=sa.String(32)
    )