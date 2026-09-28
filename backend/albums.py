from functools import lru_cache
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from PIL import Image, ImageFilter, ImageOps
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import and_, case, delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from backend.auth import session
from backend.db import connect
from backend.media import now_iso
from backend.models import Album, AlbumCover, AlbumPhoto, Photo

router = APIRouter(prefix="/api/albums", dependencies=[Depends(session)], tags=["albums"])
CARD_RATIO = 1.3
MAX_COVER_CANDIDATES = 20


@lru_cache(maxsize=4096)
def centeredness(thumb: Path) -> float:
    """Estimate how much visible detail lies near the center of an album card."""
    try:
        with Image.open(thumb) as source:
            card = ImageOps.fit(source.convert("L"), (65, 50), Image.Resampling.BILINEAR)
        edge_image = card.filter(ImageFilter.FIND_EDGES)
        edges = edge_image.load()
    except (OSError, ValueError):
        return 0.5

    total = weighted = 0.0
    for y in range(3, 47):
        vertical = 1 - abs(y - 24.5) / 24.5
        for x in range(3, 62):
            strength = edges[x, y]
            total += strength
            weighted += strength * vertical * (1 - abs(x - 32) / 32)
    return weighted / total if total else 0.5


class AlbumInput(BaseModel):
    name: str = Field(min_length=1, max_length=80)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("El álbum necesita un nombre.")
        return value.strip()


class CoverInput(BaseModel):
    photo_id: str | None = Field(default=None, min_length=32, max_length=32)
    x: int = Field(default=50, ge=0, le=100)
    y: int = Field(default=50, ge=0, le=100)


class AlbumPhotosInput(BaseModel):
    ids: list[str] = Field(min_length=1, max_length=500)


@router.get("")
def albums(request: Request):
    # Inspect only the best fitting candidates so listing large albums stays bounded.
    visible_area = case(
        (Photo.width * 10 >= Photo.height * 13, Photo.height * 13.0 / (Photo.width * 10)),
        else_=Photo.width * 10.0 / (Photo.height * 13),
    )
    ranked = (
        select(
            AlbumPhoto.album_id,
            Photo.id.label("photo_id"),
            Photo.width,
            Photo.height,
            func.row_number().over(
                partition_by=AlbumPhoto.album_id,
                order_by=(visible_area.desc(), Photo.taken_at.desc(), Photo.id.desc()),
            ).label("rank"),
        )
        .join(Photo, Photo.id == AlbumPhoto.photo_id)
        .where(Photo.deleted_at.is_(None))
        .subquery()
    )
    with connect(request.app.state.settings) as db:
        rows = (
            db.execute(
                select(
                    Album.id,
                    Album.name,
                    Album.created_at,
                    func.count(Photo.id).label("count"),
                )
                .outerjoin(AlbumPhoto, Album.id == AlbumPhoto.album_id)
                .outerjoin(Photo, and_(Photo.id == AlbumPhoto.photo_id, Photo.deleted_at.is_(None)))
                .group_by(Album.id)
                .order_by(Album.created_at.desc())
            )
            .mappings()
            .all()
        )
        candidates = db.execute(
            select(ranked)
            .where(ranked.c.rank <= MAX_COVER_CANDIDATES)
            .order_by(ranked.c.album_id, ranked.c.rank)
        ).mappings().all()
        manual_covers = db.execute(
            select(AlbumCover.album_id, AlbumCover.photo_id, AlbumCover.x, AlbumCover.y)
            .join(
                AlbumPhoto,
                and_(
                    AlbumPhoto.album_id == AlbumCover.album_id,
                    AlbumPhoto.photo_id == AlbumCover.photo_id,
                ),
            )
            .join(Photo, and_(Photo.id == AlbumCover.photo_id, Photo.deleted_at.is_(None)))
        ).all()
    manual_by_id = {album_id: (photo_id, x, y) for album_id, photo_id, x, y in manual_covers}
    albums_by_id = {
        row["id"]: {
            **row,
            "cover": manual_by_id[row["id"]][0] if row["id"] in manual_by_id else None,
            "cover_photo_id": manual_by_id[row["id"]][0] if row["id"] in manual_by_id else None,
            "cover_x": manual_by_id[row["id"]][1] if row["id"] in manual_by_id else 50,
            "cover_y": manual_by_id[row["id"]][2] if row["id"] in manual_by_id else 50,
        }
        for row in rows
    }
    best_scores = {}
    for candidate in candidates:
        width, height = candidate["width"], candidate["height"]
        ratio = width / height
        visible = min(ratio / CARD_RATIO, CARD_RATIO / ratio)
        thumb = (
            request.app.state.settings.data_dir
            / "previews"
            / f"{candidate['photo_id']}-thumb.webp"
        )
        score = visible * (0.5 + 0.5 * centeredness(thumb))
        album_id = candidate["album_id"]
        if albums_by_id[album_id]["cover_photo_id"] is not None:
            continue
        if score > best_scores.get(album_id, -1):
            best_scores[album_id] = score
            albums_by_id[album_id]["cover"] = candidate["photo_id"]
    return list(albums_by_id.values())


@router.post("", status_code=201)
def create_album(body: AlbumInput, request: Request):
    album = {"id": uuid4().hex, "name": body.name, "created_at": now_iso()}
    with connect(request.app.state.settings) as db:
        db.add(Album(**album))
    return {
        **album, "count": 0, "cover": None, "cover_photo_id": None,
        "cover_x": 50, "cover_y": 50,
    }


@router.patch("/{album_id}/cover")
def set_cover(album_id: str, body: CoverInput, request: Request):
    with connect(request.app.state.settings) as db:
        if not db.get(Album, album_id):
            raise HTTPException(404, "No encontramos este álbum.")
        if body.photo_id is None:
            db.execute(delete(AlbumCover).where(AlbumCover.album_id == album_id))
            return {"cover_photo_id": None, "cover_x": 50, "cover_y": 50}
        photo = db.get(Photo, body.photo_id)
        membership = db.get(AlbumPhoto, (album_id, body.photo_id))
        if not photo or photo.deleted_at is not None or not membership:
            raise HTTPException(404, "La portada debe ser una foto de este álbum.")
        cover = db.get(AlbumCover, album_id)
        if cover is None:
            db.add(AlbumCover(album_id=album_id, photo_id=body.photo_id, x=body.x, y=body.y))
        else:
            cover.photo_id, cover.x, cover.y = body.photo_id, body.x, body.y
    return {"cover_photo_id": body.photo_id, "cover_x": body.x, "cover_y": body.y}


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


@router.post("/{album_id}/photos")
def add_photos(album_id: str, body: AlbumPhotosInput, request: Request):
    photo_ids = list(dict.fromkeys(body.ids))
    with connect(request.app.state.settings) as db:
        if not db.get(Album, album_id):
            raise HTTPException(404, "No encontramos este álbum.")
        active = db.scalars(
            select(Photo.id).where(Photo.id.in_(photo_ids), Photo.deleted_at.is_(None))
        ).all()
        if len(active) != len(photo_ids):
            raise HTTPException(404, "No encontramos todas las fotos en la biblioteca.")
        insert = pg_insert if db.bind.dialect.name == "postgresql" else sqlite_insert
        db.execute(
            insert(AlbumPhoto).on_conflict_do_nothing(),
            [{"album_id": album_id, "photo_id": photo_id} for photo_id in photo_ids],
        )
    return {"ok": True}


@router.delete("/{album_id}/photos/{photo_id}")
def remove_photo(album_id: str, photo_id: str, request: Request):
    with connect(request.app.state.settings) as db:
        db.execute(
            delete(AlbumCover).where(
                AlbumCover.album_id == album_id, AlbumCover.photo_id == photo_id
            )
        )
        db.execute(
            delete(AlbumPhoto).where(
                AlbumPhoto.album_id == album_id,
                AlbumPhoto.photo_id == photo_id,
            )
        )
    return {"ok": True}
