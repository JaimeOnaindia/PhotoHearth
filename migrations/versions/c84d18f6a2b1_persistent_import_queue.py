"""Persistent background import queue.

Revision ID: c84d18f6a2b1
Revises: 62b93a1f4d07
"""

import sqlalchemy as sa
from alembic import op

revision = "c84d18f6a2b1"
down_revision = "62b93a1f4d07"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "import_jobs",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=1024), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("updated_at", sa.String(), nullable=False),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'paused', 'completed', "
            "'completed_errors', 'canceled')",
            name=op.f("ck_import_jobs_status"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_import_jobs")),
    )
    op.create_index(
        "import_jobs_status", "import_jobs", ["status", "created_at"], unique=False
    )
    op.create_table(
        "import_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.String(length=32), nullable=False),
        sa.Column("relative_path", sa.String(length=1024), nullable=False),
        sa.Column("bytes", sa.BigInteger(), nullable=False),
        sa.Column("modified_ns", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("photo_id", sa.String(length=32), nullable=True),
        sa.Column("error", sa.String(length=500), nullable=True),
        sa.CheckConstraint(
            "attempts >= 0", name=op.f("ck_import_items_non_negative_attempts")
        ),
        sa.CheckConstraint(
            "bytes >= 0", name=op.f("ck_import_items_non_negative_bytes")
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'imported', 'duplicate', 'failed', 'canceled')",
            name=op.f("ck_import_items_status"),
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["import_jobs.id"],
            name=op.f("fk_import_items_job_id_import_jobs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["photo_id"],
            ["photos.id"],
            name=op.f("fk_import_items_photo_id_photos"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_import_items")),
        sa.UniqueConstraint(
            "job_id", "relative_path", name=op.f("uq_import_items_job_id")
        ),
    )
    op.create_index("ix_import_items_job_id", "import_items", ["job_id"], unique=False)
    op.create_index(
        "import_items_work",
        "import_items",
        ["job_id", "status", "id"],
        unique=False,
    )


def downgrade():
    op.drop_index("import_items_work", table_name="import_items")
    op.drop_index("ix_import_items_job_id", table_name="import_items")
    op.drop_table("import_items")
    op.drop_index("import_jobs_status", table_name="import_jobs")
    op.drop_table("import_jobs")
