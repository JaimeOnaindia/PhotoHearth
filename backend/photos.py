import asyncio
from pathlib import Path
from typing import Literal
from uuid import uuid4

import anyio
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select

from backend.auth import session
from backend.db import connect
from backend.media import ingest, now_iso, photo_json
from backend.models import AlbumPhoto, Photo
from backend.places import latitude_cell, longitude_cell

router = APIRouter(prefix="/api/photos", dependencies=[Depends(session)], tags=["photos"])


@router.get("")
def photos(
    request: Request,
    q: str = Query("", max_length=200),
    view: Literal["library", "favorites", "trash"] = "library",
    album: str | None = None,
    place: str | None = Query(None, pattern=r"^\d{1,5}:\d{1,5}$"),
    limit: int = Query(60, ge=1, le=120),
    offset: int = Query(0, ge=0),
):
    conditions = [Photo.deleted_at.is_not(None) if view == "trash" else Photo.deleted_at.is_(None)]
    if view == "favorites":
        conditions.append(Photo.favorite.is_(True))
    if place:
        lat_cell, lon_cell = map(int, place.split(":"))
        conditions.extend([latitude_cell() == lat_cell, longitude_cell() == lon_cell])
    if q.strip():
        conditions.append(
            or_(
                Photo.filename.icontains(q.strip(), autoescape=True),
                Photo.taken_at.contains(q.strip(), autoescape=True),
            )
        )
    if album:
        conditions.append(
            select(AlbumPhoto.photo_id)
            .where(
                AlbumPhoto.photo_id == Photo.id,
                AlbumPhoto.album_id == album,
            )
            .exists()
        )
    with connect(request.app.state.settings) as db:
        total = db.scalar(select(func.count()).select_from(Photo).where(*conditions))
        rows = db.scalars(
            select(Photo)
            .where(*conditions)
            .order_by(Photo.taken_at.desc(), Photo.id.desc())
            .limit(limit)
            .offset(offset)
        ).all()
    return {"items": [photo_json(row) for row in rows], "total": total}


@router.post("/upload", status_code=201)
async def upload(request: Request, filename: str = Query(..., min_length=1, max_length=255)):
    settings = request.app.state.settings
    filename = Path(filename.replace("\\", "/")).name
    if not filename or any(ord(char) < 32 for char in filename):
        raise HTTPException(400, "Nombre de archivo no válido.")
    length = request.headers.get("content-length")
    if length and (not length.isdigit() or int(length) > settings.max_upload):
        raise HTTPException(413, "Cada foto puede ocupar como máximo 40 MB.")
    temporary = settings.data_dir / "incoming" / uuid4().hex
    # Bound decoder concurrency to protect the home server's memory.
    async with request.app.state.upload_lock:
        try:
            received = 0
            async with await anyio.open_file(temporary, "wb") as file:
                async with asyncio.timeout(120):
                    async for chunk in request.stream():
                        received += len(chunk)
                        if received > settings.max_upload:
                            raise HTTPException(413, "Cada foto puede ocupar como máximo 40 MB.")
                        await file.write(chunk)
            if received == 0:
                raise HTTPException(400, "El archivo está vacío.")
            return await anyio.to_thread.run_sync(ingest, settings, temporary, filename)
        except TimeoutError as error:
            raise HTTPException(
                408, "La subida ha tardado demasiado. Vuelve a intentarlo."
            ) from error
        finally:
            temporary.unlink(missing_ok=True)


class LocationInput(BaseModel):
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)
    name: str = Field(default="", max_length=120)


class PhotoUpdate(BaseModel):
    favorite: bool | None = None
    trashed: bool | None = None
    location: LocationInput | None = None


@router.patch("/{photo_id}")
def update(photo_id: str, body: PhotoUpdate, request: Request):
    with connect(request.app.state.settings) as db:
        row = db.get(Photo, photo_id)
        if not row:
            raise HTTPException(404, "No encontramos esta foto.")
        if body.favorite is not None:
            row.favorite = body.favorite
        if body.trashed is not None:
            row.deleted_at = now_iso() if body.trashed else None
        if "location" in body.model_fields_set:
            row.latitude = body.location.latitude if body.location else None
            row.longitude = body.location.longitude if body.location else None
            row.location_name = (body.location.name.strip() or None) if body.location else None
        return photo_json(row)


@router.get("/{photo_id}/file")
def media(
    photo_id: str, request: Request, variant: Literal["thumb", "preview", "original"] = "thumb"
):
    settings = request.app.state.settings
    with connect(settings) as db:
        row = db.get(Photo, photo_id)
    if not row:
        raise HTTPException(404, "No encontramos esta foto.")
    if variant == "original":
        path = settings.data_dir / "originals" / f"{row.id}.{row.extension}"
        mime, filename = row.mime, row.filename
    else:
        path = settings.data_dir / "previews" / f"{row.id}-{variant}.webp"
        mime, filename = "image/webp", None
    if not path.is_file():
        raise HTTPException(404, "El archivo no está disponible en el disco.")
    return FileResponse(path, media_type=mime, filename=filename)
