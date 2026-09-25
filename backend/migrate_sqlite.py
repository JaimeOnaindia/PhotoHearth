"""Opt-in clean migration: preserve the owner, start with an empty PostgreSQL library."""

import argparse
import sqlite3
from pathlib import Path

from sqlalchemy import func, select

from backend.config import Settings
from backend.db import connect, engine_for, initialize, lock_auth
from backend.models import Album, Photo, User


def import_owner(settings: Settings, source: Path) -> None:
    if engine_for(settings).dialect.name != "postgresql":
        raise ValueError("El destino debe ser PostgreSQL.")
    source = source.resolve(strict=True)
    connection = sqlite3.connect(f"{source.as_uri()}?mode=ro", uri=True)
    try:
        row = connection.execute("SELECT name, password_hash FROM users WHERE id=1").fetchone()
    finally:
        connection.close()
    if not row:
        raise ValueError("La biblioteca SQLite no contiene la cuenta propietaria.")
    initialize(settings)
    with connect(settings) as db:
        lock_auth(db)
        if any(
            db.scalar(select(func.count()).select_from(model)) for model in (User, Photo, Album)
        ):
            raise ValueError("El destino no está vacío. No se sobrescribe ninguna biblioteca.")
        db.add(User(id=1, name=row[0], password_hash=row[1]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migración limpia SQLite → PostgreSQL")
    parser.add_argument("--source", type=Path, required=True, help="SQLite de una copia verificada")
    parser.add_argument(
        "--owner-only",
        action="store_true",
        required=True,
        help="Conserva solo la cuenta; no importa fotos ni álbumes",
    )
    arguments = parser.parse_args()
    import_owner(Settings(), arguments.source)
    print("Cuenta importada. Biblioteca nueva vacía. El origen no se ha modificado.")
