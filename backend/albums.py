from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import and_, delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from backend.auth import session
from backend.db import connect
from backend.media import now_iso
from backend.models import Album, AlbumPhoto, Photo

router = APIRouter(prefix="/api/albums", dependencies=[Depends(session)], tags=["albums"])


class AlbumInput(BaseModel):
    name: str = Field(min_length=1, max_length=80)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("El álbum necesita un nombre.")
        return value.strip()


@router.get("")
def albums(request: Request):
    cover = (
        select(Photo.id)
        .join(AlbumPhoto, AlbumPhoto.photo_id == Photo.id)
        .where(AlbumPhoto.album_id == Album.id, Photo.deleted_at.is_(None))
        .order_by(Photo.taken_at.desc(), Photo.id.desc())
        .limit(1)
        .correlate(Album)
        .scalar_subquery()
    )
    with connect(request.app.state.settings) as db:
        rows = (
            db.execute(
                select(
                    Album.id,
                    Album.name,
                    Album.created_at,
                    func.count(Photo.id).label("count"),
                    cover.label("cover"),
                )
                .outerjoin(AlbumPhoto, Album.id == AlbumPhoto.album_id)
                .outerjoin(Photo, and_(Photo.id == AlbumPhoto.photo_id, Photo.deleted_at.is_(None)))
                .group_by(Album.id)
                .order_by(Album.created_at.desc())
            )
            .mappings()
            .all()
        )
    return [dict(row) for row in rows]


@router.post("", status_code=201)
def create_album(body: AlbumInput, request: Request):
    album = {"id": uuid4().hex, "name": body.name, "created_at": now_iso()}
    with connect(request.app.state.settings) as db:
        db.add(Album(**album))
    return {**album, "count": 0, "cover": None}


@router.put("/{album_id}/photos/{photo_id}")
def add_photo(album_id: str, photo_id: str, request: Request):
    with connect(request.app.state.settings) as db:
        if not db.get(Album, album_id):
            raise HTTPException(404, "No encontramos este álbum.")
        photo = db.get(Photo, photo_id)
        if not photo or photo.deleted_at is not None:
            raise HTTPException(404, "No encontramos esta foto en la biblioteca.")
        insert = pg_insert if db.bind.dialect.name == "postgresql" else sqlite_insert
        db.execute(
            insert(AlbumPhoto).values(album_id=album_id, photo_id=photo_id).on_conflict_do_nothing()
        )
    return {"ok": True}


@router.delete("/{album_id}/photos/{photo_id}")
def remove_photo(album_id: str, photo_id: str, request: Request):
    with connect(request.app.state.settings) as db:
        db.execute(
            delete(AlbumPhoto).where(
                AlbumPhoto.album_id == album_id,
                AlbumPhoto.photo_id == photo_id,
            )
        )
    return {"ok": True}
