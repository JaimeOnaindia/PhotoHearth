import os
import shutil
import stat
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func, insert, select, update
from sqlalchemy.orm import Session

from backend.config import Settings
from backend.db import connect
from backend.media import ingest, now_iso
from backend.models import ImportItem, ImportJob

SUPPORTED_SUFFIXES = frozenset(
    {".jpg", ".jpeg", ".jpe", ".jfif", ".png", ".webp", ".heic", ".heif", ".mpo"}
)
ACTIVE_JOB_STATUSES = ("queued", "running")
INSERT_CHUNK_SIZE = 1_000


class ImportProblem(ValueError):
    """A safe, user-facing import error."""


class ImportUnavailable(ImportProblem):
    """The administrator has not provided an accessible import directory."""


class ImportNotFound(ImportProblem):
    """The requested import job does not exist."""


def _import_root(settings: Settings) -> Path:
    if settings.import_dir is None:
        raise ImportUnavailable("No hay una carpeta de importación configurada.")
    try:
        root = settings.import_dir.resolve(strict=True)
    except FileNotFoundError as error:
        raise ImportUnavailable("La carpeta de importación no existe.") from error
    if not root.is_dir():
        raise ImportUnavailable("La ruta de importación no es una carpeta.")
    return root


def _safe_relative(value: str) -> Path:
    if "\x00" in value:
        raise ImportProblem("La ruta de importación no es válida.")
    relative = Path(value.strip() or ".")
    if relative.is_absolute() or ".." in relative.parts:
        raise ImportProblem("La ruta debe estar dentro de la carpeta de importación.")
    return relative


def _reject_symlink_components(root: Path, relative: Path) -> None:
    current = root
    for part in relative.parts:
        if part in ("", "."):
            continue
        current = current / part
        if current.is_symlink():
            raise ImportProblem("No se permiten enlaces simbólicos en la importación.")


def _source_directory(settings: Settings, source: str) -> tuple[Path, Path, str]:
    root = _import_root(settings)
    relative = _safe_relative(source)
    _reject_symlink_components(root, relative)
    candidate = root / relative
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except (FileNotFoundError, ValueError) as error:
        raise ImportProblem("La carpeta solicitada no existe dentro de la importación.") from error
    if not resolved.is_dir():
        raise ImportProblem("La ruta solicitada no es una carpeta.")
    normalized = resolved.relative_to(root)
    source_name = "." if normalized == Path(".") else _safe_text_path(normalized)
    return root, resolved, source_name


def _safe_text_path(relative: Path) -> str:
    value = relative.as_posix()
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as error:
        raise ImportProblem("Hay un nombre de archivo que no es UTF-8 válido.") from error
    if len(value) > 1_024:
        raise ImportProblem("Hay una ruta de archivo demasiado larga para importarla.")
    return value


def _raise_walk_error(error: OSError) -> None:
    raise error


def _scan(settings: Settings, root: Path, source_directory: Path) -> list[dict]:
    files: list[dict] = []
    try:
        for directory, directory_names, filenames in os.walk(
            source_directory,
            topdown=True,
            onerror=_raise_walk_error,
            followlinks=False,
        ):
            directory_path = Path(directory)
            directory_names[:] = sorted(
                name
                for name in directory_names
                if not (directory_path / name).is_symlink()
            )
            for filename in sorted(filenames):
                path = directory_path / filename
                if path.suffix.lower() not in SUPPORTED_SUFFIXES or path.is_symlink():
                    continue
                metadata = path.stat(follow_symlinks=False)
                if not stat.S_ISREG(metadata.st_mode):
                    continue
                relative_path = _safe_text_path(path.relative_to(root))
                files.append(
                    {
                        "relative_path": relative_path,
                        "bytes": metadata.st_size,
                        "modified_ns": metadata.st_mtime_ns,
                        "status": "pending",
                        "attempts": 0,
                    }
                )
                if len(files) > settings.import_max_files:
                    raise ImportProblem(
                        f"La carpeta supera el límite de {settings.import_max_files} archivos."
                    )
    except OSError as error:
        raise ImportProblem(
            "No se ha podido leer por completo la carpeta de importación."
        ) from error
    return files


def _counts(db: Session, job_id: str) -> dict[str, int]:
    rows = db.execute(
        select(ImportItem.status, func.count(ImportItem.id))
        .where(ImportItem.job_id == job_id)
        .group_by(ImportItem.status)
    )
    return {status: count for status, count in rows}


def _job_json(db: Session, job: ImportJob) -> dict:
    counts = _counts(db, job.id)
    total = sum(counts.values())
    pending = counts.get("pending", 0)
    running = counts.get("running", 0)
    return {
        "id": job.id,
        "source": job.source,
        "status": job.status,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "total": total,
        "finished": total - pending - running,
        "pending": pending,
        "running": running,
        "imported": counts.get("imported", 0),
        "duplicates": counts.get("duplicate", 0),
        "failed": counts.get("failed", 0),
        "canceled": counts.get("canceled", 0),
    }


def create_import_job(settings: Settings, source: str = ".") -> dict:
    root, source_directory, source_name = _source_directory(settings, source)
    files = _scan(settings, root, source_directory)
    timestamp = now_iso()
    job = ImportJob(
        id=uuid4().hex,
        source=source_name,
        status="queued" if files else "completed",
        created_at=timestamp,
        updated_at=timestamp,
    )
    with connect(settings) as db:
        db.add(job)
        db.flush()
        for offset in range(0, len(files), INSERT_CHUNK_SIZE):
            rows = [
                {**entry, "job_id": job.id}
                for entry in files[offset : offset + INSERT_CHUNK_SIZE]
            ]
            db.execute(insert(ImportItem), rows)
        return _job_json(db, job)


def import_job(settings: Settings, job_id: str) -> dict:
    with connect(settings) as db:
        job = db.get(ImportJob, job_id)
        if job is None:
            raise ImportNotFound("La importación no existe.")
        return _job_json(db, job)


def list_import_jobs(settings: Settings, limit: int = 20) -> list[dict]:
    safe_limit = max(1, min(limit, 100))
    with connect(settings) as db:
        jobs = db.scalars(
            select(ImportJob)
            .order_by(ImportJob.created_at.desc(), ImportJob.id.desc())
            .limit(safe_limit)
        ).all()
        return [_job_json(db, job) for job in jobs]


def _item_path(root: Path, relative_path: str) -> Path:
    relative = _safe_relative(relative_path)
    _reject_symlink_components(root, relative)
    candidate = root / relative
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except (FileNotFoundError, ValueError) as error:
        raise ImportProblem("El archivo ya no existe en la carpeta de importación.") from error
    if resolved.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise ImportProblem("El archivo ya no tiene un formato admitido.")
    metadata = resolved.stat(follow_symlinks=False)
    if not stat.S_ISREG(metadata.st_mode):
        raise ImportProblem("La ruta ya no corresponde a un archivo normal.")
    return resolved


def _refresh_failed_item(root: Path, item: ImportItem, max_upload: int) -> bool:
    try:
        path = _item_path(root, item.relative_path)
        metadata = path.stat(follow_symlinks=False)
        if metadata.st_size > max_upload:
            raise ImportProblem("El archivo supera el tamaño máximo permitido.")
    except (ImportProblem, OSError) as error:
        item.error = _error_message(error)
        return False
    item.bytes = metadata.st_size
    item.modified_ns = metadata.st_mtime_ns
    item.status = "pending"
    item.error = None
    item.photo_id = None
    return True


def control_import_job(settings: Settings, job_id: str, action: str) -> dict:
    if action not in {"pause", "resume", "retry", "cancel"}:
        raise ImportProblem("La acción de importación no es válida.")
    root = _import_root(settings) if action == "retry" else None
    timestamp = now_iso()
    with connect(settings) as db:
        statement = select(ImportJob).where(ImportJob.id == job_id)
        if db.bind.dialect.name == "postgresql":
            statement = statement.with_for_update()
        job = db.scalar(statement)
        if job is None:
            raise ImportNotFound("La importación no existe.")

        if action == "pause" and job.status in ACTIVE_JOB_STATUSES:
            job.status = "paused"
        elif action == "resume" and job.status in {"paused", "canceled"}:
            if job.status == "canceled":
                db.execute(
                    update(ImportItem)
                    .where(ImportItem.job_id == job.id, ImportItem.status == "canceled")
                    .values(status="pending", error=None)
                )
            job.status = "queued"
        elif action == "cancel" and job.status in {*ACTIVE_JOB_STATUSES, "paused"}:
            db.execute(
                update(ImportItem)
                .where(ImportItem.job_id == job.id, ImportItem.status == "pending")
                .values(status="canceled")
            )
            job.status = "canceled"
        elif action == "retry":
            failed = db.scalars(
                select(ImportItem).where(
                    ImportItem.job_id == job.id, ImportItem.status == "failed"
                )
            ).all()
            reset = sum(
                _refresh_failed_item(root, item, settings.max_upload) for item in failed
            )
            if reset:
                job.status = "queued"
        job.updated_at = timestamp
        _finish_job(db, job, timestamp)
        return _job_json(db, job)


def _claim_next(settings: Settings) -> tuple[int, str, str, int, int] | None:
    with connect(settings) as db:
        statement = (
            select(ImportItem)
            .join(ImportJob, ImportJob.id == ImportItem.job_id)
            .where(
                ImportJob.status.in_(ACTIVE_JOB_STATUSES),
                ImportItem.status == "pending",
            )
            .order_by(ImportJob.created_at, ImportItem.id)
            .limit(1)
        )
        if db.bind.dialect.name == "postgresql":
            statement = statement.with_for_update(skip_locked=True, of=ImportItem)
        item = db.scalar(statement)
        if item is None:
            return None
        item.status = "running"
        item.attempts += 1
        timestamp = now_iso()
        db.execute(
            update(ImportJob)
            .where(ImportJob.id == item.job_id, ImportJob.status == "queued")
            .values(status="running", updated_at=timestamp)
        )
        return item.id, item.job_id, item.relative_path, item.bytes, item.modified_ns


def _copy_source(
    settings: Settings, root: Path, relative_path: str, expected_bytes: int, expected_ns: int
) -> tuple[Path, str]:
    source = _item_path(root, relative_path)
    before = source.stat(follow_symlinks=False)
    if before.st_size != expected_bytes or before.st_mtime_ns != expected_ns:
        raise ImportProblem(
            "El archivo cambió después de crear la importación; vuelve a intentarlo."
        )
    if before.st_size > settings.max_upload:
        raise ImportProblem("El archivo supera el tamaño máximo permitido.")
    temporary = settings.data_dir / "incoming" / f"import-{uuid4().hex}"
    try:
        shutil.copyfile(source, temporary, follow_symlinks=False)
        after = source.stat(follow_symlinks=False)
        if (
            after.st_size != before.st_size
            or after.st_mtime_ns != before.st_mtime_ns
            or temporary.stat().st_size != before.st_size
        ):
            raise ImportProblem(
                "El archivo cambió mientras se estaba copiando; vuelve a intentarlo."
            )
        return temporary, source.name
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _error_message(error: Exception) -> str:
    if isinstance(error, HTTPException):
        detail = str(error.detail)
    elif isinstance(error, ImportProblem):
        detail = str(error)
    elif isinstance(error, PermissionError):
        detail = "No hay permiso para leer el archivo."
    elif isinstance(error, FileNotFoundError):
        detail = "El archivo ya no existe en la carpeta de importación."
    elif isinstance(error, OSError) and error.errno == 28:
        detail = "No queda espacio en el disco."
    elif isinstance(error, OSError):
        detail = "No se ha podido leer o guardar el archivo."
    else:
        detail = "No se ha podido importar el archivo."
    return detail[:500]


def _finish_job(db: Session, job: ImportJob, timestamp: str | None = None) -> None:
    counts = _counts(db, job.id)
    if counts.get("pending", 0) or counts.get("running", 0):
        return
    if job.status != "canceled":
        job.status = "completed_errors" if counts.get("failed", 0) else "completed"
    job.updated_at = timestamp or now_iso()


def process_next_import(settings: Settings) -> bool:
    claimed = _claim_next(settings)
    if claimed is None:
        return False
    item_id, job_id, relative_path, expected_bytes, expected_ns = claimed
    temporary: Path | None = None
    status = "failed"
    photo_id = None
    error_message = None
    try:
        root = _import_root(settings)
        temporary, filename = _copy_source(
            settings, root, relative_path, expected_bytes, expected_ns
        )
        result = ingest(settings, temporary, filename)
        status = "duplicate" if result["duplicate"] else "imported"
        photo_id = result["photo"]["id"]
    except Exception as error:
        error_message = _error_message(error)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)

    timestamp = now_iso()
    with connect(settings) as db:
        item = db.get(ImportItem, item_id)
        if item is not None:
            item.status = status
            item.photo_id = photo_id
            item.error = error_message
        job = db.get(ImportJob, job_id)
        if job is not None:
            job.updated_at = timestamp
            _finish_job(db, job, timestamp)
    return True


def drain_imports(settings: Settings, limit: int | None = None) -> int:
    processed = 0
    while limit is None or processed < limit:
        if not process_next_import(settings):
            break
        processed += 1
    return processed


def recover_imports(settings: Settings) -> int:
    """Restore interrupted queue items and discard incomplete temporary copies."""
    recovered = 0
    timestamp = now_iso()
    with connect(settings) as db:
        interrupted = db.scalars(
            select(ImportItem).where(ImportItem.status == "running")
        ).all()
        for item in interrupted:
            job = db.get(ImportJob, item.job_id)
            item.status = "canceled" if job and job.status == "canceled" else "pending"
            recovered += 1
        interrupted_job_ids = {item.job_id for item in interrupted}
        jobs = db.scalars(
            select(ImportJob).where(
                ImportJob.status.in_((*ACTIVE_JOB_STATUSES, "paused"))
            )
        ).all()
        for job in jobs:
            changed = job.id in interrupted_job_ids
            if job.status == "running":
                job.status = "queued"
                changed = True
            if job.status in {*ACTIVE_JOB_STATUSES, "paused"}:
                previous_status = job.status
                _finish_job(db, job, timestamp)
                changed = changed or job.status != previous_status
            if changed:
                job.updated_at = timestamp

    incoming = settings.data_dir / "incoming"
    if incoming.exists():
        for temporary in incoming.glob("import-*"):
            if temporary.is_file() or temporary.is_symlink():
                temporary.unlink(missing_ok=True)
    return recovered
