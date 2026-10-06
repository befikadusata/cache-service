"""Create persistent transformation and complete payload storage."""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "transformations",
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("source_digest", sa.LargeBinary(32), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("result", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("version", "source_digest"),
        sa.CheckConstraint("octet_length(source_digest) = 32", name="source_digest_length"),
    )
    op.create_table(
        "payloads",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("input_digest", sa.LargeBinary(32), nullable=False, unique=True),
        sa.Column("canonical_input", sa.Text(), nullable=False),
        sa.Column("output", sa.Text(), nullable=False),
        sa.CheckConstraint("octet_length(input_digest) = 32", name="input_digest_length"),
    )


def downgrade():
    op.drop_table("payloads")
    op.drop_table("transformations")
