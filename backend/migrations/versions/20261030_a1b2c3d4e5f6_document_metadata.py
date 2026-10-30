"""document metadata: authority, version, effective date, family, supersession

Revision ID: a1b2c3d4e5f6
Revises: 0210e47d3b23
Create Date: 2026-10-30 09:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "0210e47d3b23"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("authority", sa.String(20), nullable=False, server_default="upload"))
    op.add_column("documents", sa.Column("version", sa.String(40), nullable=True))
    op.add_column("documents", sa.Column("effective_date", sa.String(10), nullable=True))
    op.add_column("documents", sa.Column("doc_family", sa.String(100), nullable=True))
    op.add_column(
        "documents",
        sa.Column("supersedes", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )


def downgrade() -> None:
    for column in ("supersedes", "doc_family", "effective_date", "version", "authority"):
        op.drop_column("documents", column)
