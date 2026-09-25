from sqlalchemy import CheckConstraint, ForeignKey, Index, MetaData, String
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


Index("photos_timeline", Photo.deleted_at, Photo.taken_at.desc(), Photo.id.desc())


class Album(Base):
    __tablename__ = "albums"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[str]


class AlbumPhoto(Base):
    __tablename__ = "album_photos"
    album_id: Mapped[str] = mapped_column(
        ForeignKey("albums.id", ondelete="CASCADE"), primary_key=True
    )
    photo_id: Mapped[str] = mapped_column(
        ForeignKey("photos.id", ondelete="CASCADE"), primary_key=True
    )
