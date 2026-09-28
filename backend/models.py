from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    MetaData,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("id = 1", name="single_owner"),)
    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    name: Mapped[str] = mapped_column(String(80))
    password_hash: Mapped[str]


class LoginSession(Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    csrf: Mapped[str]
    expires: Mapped[int]


class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    __table_args__ = (Index("attempts_address", "address", "attempted"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    address: Mapped[str]
    attempted: Mapped[int]


class Photo(Base):
    __tablename__ = "photos"
    __table_args__ = (
        CheckConstraint(
            "(latitude IS NULL AND longitude IS NULL) OR "
            "(latitude IS NOT NULL AND longitude IS NOT NULL AND "
            "latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180)",
            name="valid_coordinates",
        ),
    )
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    sha256: Mapped[str] = mapped_column(String(64), unique=True)
    filename: Mapped[str] = mapped_column(String(255))
    extension: Mapped[str]
    mime: Mapped[str]
    bytes: Mapped[int]
    width: Mapped[int]
    height: Mapped[int]
    taken_at: Mapped[str]
    uploaded_at: Mapped[str]
    favorite: Mapped[bool] = mapped_column(default=False, server_default="0")
    deleted_at: Mapped[str | None]
    latitude: Mapped[float | None]
    longitude: Mapped[float | None]
    location_name: Mapped[str | None] = mapped_column(String(120))


Index("photos_timeline", Photo.deleted_at, Photo.taken_at.desc(), Photo.id.desc())
Index("photos_location", Photo.deleted_at, Photo.latitude, Photo.longitude)


class Country(Base):
    __tablename__ = "countries"
    code: Mapped[str] = mapped_column(String(2), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))


class Locality(Base):
    __tablename__ = "localities"
    __table_args__ = (
        CheckConstraint("latitude BETWEEN -90 AND 90", name="valid_latitude"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="valid_longitude"),
        CheckConstraint("population >= 0", name="non_negative_population"),
    )
    geoname_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    feature_code: Mapped[str] = mapped_column(String(10))
    country_code: Mapped[str] = mapped_column(ForeignKey("countries.code"))
    admin1: Mapped[str | None] = mapped_column(String(50))
    admin2: Mapped[str | None] = mapped_column(String(100))
    population: Mapped[int] = mapped_column(BigInteger)


Index("localities_coordinates", Locality.latitude, Locality.longitude)


class Album(Base):
    __tablename__ = "albums"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[str]


class AlbumCover(Base):
    __tablename__ = "album_covers"
    __table_args__ = (
        CheckConstraint("x BETWEEN 0 AND 100", name="valid_x"),
        CheckConstraint("y BETWEEN 0 AND 100", name="valid_y"),
    )
    album_id: Mapped[str] = mapped_column(
        ForeignKey("albums.id", ondelete="CASCADE"), primary_key=True
    )
    photo_id: Mapped[str] = mapped_column(ForeignKey("photos.id", ondelete="CASCADE"))
    x: Mapped[int] = mapped_column(default=50, server_default="50")
    y: Mapped[int] = mapped_column(default=50, server_default="50")


class AlbumPhoto(Base):
    __tablename__ = "album_photos"
    album_id: Mapped[str] = mapped_column(
        ForeignKey("albums.id", ondelete="CASCADE"), primary_key=True
    )
    photo_id: Mapped[str] = mapped_column(
        ForeignKey("photos.id", ondelete="CASCADE"), primary_key=True
    )


class ImportJob(Base):
    __tablename__ = "import_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'paused', 'completed', "
            "'completed_errors', 'canceled')",
            name="status",
        ),
    )
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    source: Mapped[str] = mapped_column(String(1024))
    status: Mapped[str] = mapped_column(String(24))
    created_at: Mapped[str]
    updated_at: Mapped[str]


Index("import_jobs_status", ImportJob.status, ImportJob.created_at)


class ImportItem(Base):
    __tablename__ = "import_items"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'imported', 'duplicate', 'failed', 'canceled')",
            name="status",
        ),
        CheckConstraint("bytes >= 0", name="non_negative_bytes"),
        CheckConstraint("attempts >= 0", name="non_negative_attempts"),
        UniqueConstraint("job_id", "relative_path"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[str] = mapped_column(
        ForeignKey("import_jobs.id", ondelete="CASCADE"), index=True
    )
    relative_path: Mapped[str] = mapped_column(String(1024))
    bytes: Mapped[int] = mapped_column(BigInteger)
    modified_ns: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(20), default="pending", server_default="pending")
    attempts: Mapped[int] = mapped_column(default=0, server_default="0")
    photo_id: Mapped[str | None] = mapped_column(
        ForeignKey("photos.id", ondelete="SET NULL"), nullable=True
    )
    error: Mapped[str | None] = mapped_column(String(500), nullable=True)


Index("import_items_work", ImportItem.job_id, ImportItem.status, ImportItem.id)
