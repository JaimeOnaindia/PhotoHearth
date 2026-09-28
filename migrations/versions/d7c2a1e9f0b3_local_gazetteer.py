"""Local GeoNames countries and populated places.

Revision ID: d7c2a1e9f0b3
Revises: c84d18f6a2b1
"""

import sqlalchemy as sa
from alembic import op

revision = "d7c2a1e9f0b3"
down_revision = "c84d18f6a2b1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "countries",
        sa.Column("code", sa.String(length=2), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.PrimaryKeyConstraint("code", name=op.f("pk_countries")),
    )
    op.create_table(
        "localities",
        sa.Column("geoname_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("feature_code", sa.String(length=10), nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("admin1", sa.String(length=50), nullable=True),
        sa.Column("admin2", sa.String(length=100), nullable=True),
        sa.Column("population", sa.BigInteger(), nullable=False),
        sa.CheckConstraint(
            "latitude BETWEEN -90 AND 90", name=op.f("ck_localities_valid_latitude")
        ),
        sa.CheckConstraint(
            "longitude BETWEEN -180 AND 180", name=op.f("ck_localities_valid_longitude")
        ),
        sa.CheckConstraint("population >= 0", name=op.f("ck_localities_non_negative_population")),
        sa.ForeignKeyConstraint(
            ["country_code"], ["countries.code"], name=op.f("fk_localities_country_code_countries")
        ),
        sa.PrimaryKeyConstraint("geoname_id", name=op.f("pk_localities")),
    )
    op.create_index(
        "localities_coordinates", "localities", ["latitude", "longitude"], unique=False
    )


def downgrade():
    op.drop_index("localities_coordinates", table_name="localities")
    op.drop_table("localities")
    op.drop_table("countries")
