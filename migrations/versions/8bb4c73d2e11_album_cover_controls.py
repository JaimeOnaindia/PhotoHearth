"""Manual album cover and focal position.

Revision ID: 8bb4c73d2e11
Revises: d7c2a1e9f0b3
"""

import sqlalchemy as sa
from alembic import op

revision = "8bb4c73d2e11"
down_revision = "d7c2a1e9f0b3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "album_covers",
        sa.Column("album_id", sa.String(length=32), nullable=False),
        sa.Column("photo_id", sa.String(length=32), nullable=False),
        sa.Column("x", sa.Integer(), server_default="50", nullable=False),
        sa.Column("y", sa.Integer(), server_default="50", nullable=False),
        sa.CheckConstraint("x BETWEEN 0 AND 100", name=op.f("ck_album_covers_valid_x")),
        sa.CheckConstraint("y BETWEEN 0 AND 100", name=op.f("ck_album_covers_valid_y")),
        sa.ForeignKeyConstraint(
            ["album_id"], ["albums.id"], name=op.f("fk_album_covers_album_id_albums"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["photo_id"], ["photos.id"], name=op.f("fk_album_covers_photo_id_photos"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("album_id", name=op.f("pk_album_covers")),
    )


def downgrade():
    op.drop_table("album_covers")
