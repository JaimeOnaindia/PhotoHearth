"""Consistent SQLite snapshot plus immutable photo files, streamed as a tar archive."""

import sqlite3
import sys
import tarfile
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.config import Settings


def export(settings: Settings, output) -> None:
    if not settings.database.is_file():
        raise FileNotFoundError("La biblioteca todavía no existe.")
    with TemporaryDirectory(prefix="photohearth-backup-") as directory:
        snapshot = Path(directory) / "library.sqlite3"
        source = sqlite3.connect(f"{settings.database.as_uri()}?mode=ro", uri=True)
        target = sqlite3.connect(snapshot)
        try:
            source.backup(target)
            if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeError("La base de datos no supera la comprobación de integridad.")
            # Restored libraries must require a new login.
            target.execute("DELETE FROM sessions")
            target.execute("DELETE FROM login_attempts")
            target.commit()
            photos = target.execute("SELECT id, extension FROM photos").fetchall()
        finally:
            source.close()
            target.close()
        with tarfile.open(fileobj=output, mode="w|") as archive:
            archive.add(snapshot, arcname="library.sqlite3")
            for photo_id, extension in photos:
                paths = (
                    f"originals/{photo_id}.{extension}",
                    f"previews/{photo_id}-thumb.webp",
                    f"previews/{photo_id}-preview.webp",
                )
                for relative in paths:
                    path = settings.data_dir / relative
                    if not path.is_file() or path.is_symlink():
                        raise FileNotFoundError(f"Falta un archivo de la biblioteca: {relative}")
                    archive.add(path, arcname=relative, recursive=False)


if __name__ == "__main__":
    export(Settings(), sys.stdout.buffer)
