import hashlib
import warnings
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException
from PIL import Image, ImageOps, UnidentifiedImageError
from pillow_heif import register_heif_opener
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from backend.config import Settings
from backend.db import connect
from backend.models import Photo

register_heif_opener()
Image.MAX_IMAGE_PIXELS = 60_000_000
FORMATS = {
    "JPEG": ("jpg", "image/jpeg"),
    "PNG": ("png", "image/png"),
    "WEBP": ("webp", "image/webp"),
    "HEIF": ("heic", "image/heic"),
}


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def photo_json(row: Photo) -> dict:
    return {
        column.name: getattr(row, column.name)
        for column in Photo.__table__.columns
        if column.name not in {"sha256", "extension", "mime"}
    }


def ingest(settings: Settings, temporary: Path, filename: str) -> dict:
    with temporary.open("rb") as file:
        checksum = hashlib.file_digest(file, "sha256").hexdigest()
    with connect(settings) as db:
        existing = db.scalar(select(Photo).where(Photo.sha256 == checksum))
    if existing:
        return {"photo": photo_json(existing), "duplicate": True}

    photo_id = uuid4().hex
    created_files = []
    uploaded = now_iso()
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(temporary) as source:
                if source.format not in FORMATS:
                    raise HTTPException(415, "Formato no compatible. Usa JPEG, PNG, WebP o HEIC.")
                extension, mime = FORMATS[source.format]
                source.verify()
            with Image.open(temporary) as source:
                taken = uploaded
                try:
                    exif = source.getexif()
                    original_date = exif.get_ifd(0x8769).get(36867) or exif.get(306)
                    if original_date:
                        taken = datetime.strptime(
                            str(original_date), "%Y:%m:%d %H:%M:%S"
                        ).isoformat()
                except (ValueError, TypeError, AttributeError, KeyError, OSError):
                    pass
                source = ImageOps.exif_transpose(source)
                width, height = source.size
                source.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
                preview = source.convert("RGB")
                for suffix, size, quality in (("preview", 1600, 85), ("thumb", 480, 78)):
                    target = settings.data_dir / "previews" / f"{photo_id}-{suffix}.webp"
                    created_files.append(target)
                    preview.thumbnail((size, size), Image.Resampling.LANCZOS)
                    preview.save(target, "WEBP", quality=quality, exif=b"")
        original = settings.data_dir / "originals" / f"{photo_id}.{extension}"
        size = temporary.stat().st_size
        temporary.replace(original)
        created_files.append(original)
        with connect(settings) as db:
            result = Photo(
                id=photo_id,
                sha256=checksum,
                filename=filename,
                extension=extension,
                mime=mime,
                bytes=size,
                width=width,
                height=height,
                taken_at=taken,
                uploaded_at=uploaded,
            )
            db.add(result)
            db.flush()
        return {"photo": photo_json(result), "duplicate": False}
    except Exception as error:
        for target in created_files:
            target.unlink(missing_ok=True)
        if isinstance(error, IntegrityError):
            with connect(settings) as db:
                existing = db.scalar(select(Photo).where(Photo.sha256 == checksum))
            if existing:
                return {"photo": photo_json(existing), "duplicate": True}
        if isinstance(
            error,
            (
                UnidentifiedImageError,
                Image.DecompressionBombError,
                Image.DecompressionBombWarning,
                ValueError,
                SyntaxError,
            ),
        ):
            raise HTTPException(
                415, "La imagen no es válida o supera los 60 megapíxeles."
            ) from error
        if isinstance(error, OSError):
            if error.errno == 28:
                raise HTTPException(507, "No queda espacio en el disco.") from error
            raise HTTPException(422, "No se ha podido procesar la imagen.") from error
        raise
