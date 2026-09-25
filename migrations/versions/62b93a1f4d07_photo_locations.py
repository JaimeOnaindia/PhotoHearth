"""Private photo coordinates and optional place names."""

import sqlalchemy as sa
from alembic import op

revision = "62b93a1f4d07"
down_revision = "97e1eb47e302"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name == "sqlite":
        # Rebuilding photos with foreign keys enabled would cascade-delete album links.
        op.add_column("photos", sa.Column("latitude", sa.Float(), nullable=True))
        op.add_column("photos", sa.Column("longitude", sa.Float(), nullable=True))
        op.execute(
            "ALTER TABLE photos ADD COLUMN location_name VARCHAR(120) "
            "CONSTRAINT ck_photos_valid_coordinates CHECK ("
            "(latitude IS NULL AND longitude IS NULL) OR "
            "(latitude IS NOT NULL AND longitude IS NOT NULL AND "
            "latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180))"
        )
        op.create_index("photos_location", "photos", ["deleted_at", "latitude", "longitude"])
        return
    with op.batch_alter_table("photos") as batch:
        batch.add_column(sa.Column("latitude", sa.Float(), nullable=True))
        batch.add_column(sa.Column("longitude", sa.Float(), nullable=True))
        batch.add_column(sa.Column("location_name", sa.String(120), nullable=True))
        batch.create_check_constraint(
            "valid_coordinates",
            "(latitude IS NULL AND longitude IS NULL) OR "
            "(latitude IS NOT NULL AND longitude IS NOT NULL AND "
            "latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180)",
        )
        batch.create_index("photos_location", ["deleted_at", "latitude", "longitude"])


def downgrade():
    if op.get_bind().dialect.name == "sqlite":
        op.drop_index("photos_location", table_name="photos")
        for column in ("location_name", "longitude", "latitude"):
            op.drop_column("photos", column)
        return
    with op.batch_alter_table("photos") as batch:
        batch.drop_index("photos_location")
        batch.drop_constraint("valid_coordinates", type_="check")
        batch.drop_column("location_name")
        batch.drop_column("longitude")
        batch.drop_column("latitude")
