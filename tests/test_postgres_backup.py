import io
import sqlite3
import subprocess
import tarfile
from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy import create_engine, text

from backend.backup import export
from backend.db import connect, engine_for, initialize
from backend.media import ingest
from backend.migrate_sqlite import import_owner
from backend.models import LoginSession, Photo, User
from backend.postgres_backup import pg_environment


def test_owner_only_import_is_non_destructive(db_settings, tmp_path):
    if not db_settings.database_url:
        pytest.skip("PostgreSQL-specific migration")
    source = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(source) as db:
        db.execute("CREATE TABLE users (id INTEGER, name TEXT, password_hash TEXT)")
        db.execute("INSERT INTO users VALUES (1, 'Jaime', 'preserved-password-hash')")
    original = source.read_bytes()
    import_owner(db_settings, source)
    with connect(db_settings) as db:
        assert db.get(User, 1).password_hash == "preserved-password-hash"
    with pytest.raises(ValueError, match="no está vacío"):
        import_owner(db_settings, source)
    assert source.read_bytes() == original


def test_owner_import_reads_wal_snapshot_without_creating_sidecars(db_settings, tmp_path):
    if not db_settings.database_url:
        pytest.skip("PostgreSQL-specific migration")
    live = sqlite3.connect(tmp_path / "live.sqlite3")
    source = tmp_path / "snapshot.sqlite3"
    try:
        live.execute("PRAGMA journal_mode=WAL")
        live.execute("CREATE TABLE users (id INTEGER, name TEXT, password_hash TEXT)")
        live.execute("INSERT INTO users VALUES (1, 'Jaime', 'test-hash')")
        live.commit()
        target = sqlite3.connect(source)
        live.backup(target)
        target.close()
    finally:
        live.close()
    original = source.read_bytes()
    assert original[18:20] == b"\x02\x02"  # WAL-mode database header.
    import_owner(db_settings, source)
    assert source.read_bytes() == original
    assert not Path(f"{source}-wal").exists()
    assert not Path(f"{source}-shm").exists()


def test_postgres_backup_restores_files_and_database(db_settings, tmp_path):
    if not db_settings.database_url:
        pytest.skip("PostgreSQL-specific backup")
    version = subprocess.check_output(["pg_dump", "--version"], text=True)
    if int(version.split()[2].split(".")[0]) < 17:
        pytest.skip("The PostgreSQL backup test needs pg_dump 17+ (included in Docker/CI)")
    initialize(db_settings)
    with connect(db_settings) as db:
        db.add(User(id=1, name="Jaime", password_hash="test-hash"))
        db.add(LoginSession(token_hash="old-session", csrf="old-csrf", expires=999))
    incoming = db_settings.data_dir / "incoming" / "test.jpg"
    Image.new("RGB", (20, 20), "coral").save(incoming)
    original = incoming.read_bytes()
    photo = ingest(db_settings, incoming, "test.jpg")["photo"]
    output = io.BytesIO()
    export(db_settings, output)
    output.seek(0)
    restored = tmp_path / "restored"
    with tarfile.open(fileobj=output) as archive:
        archive.extractall(restored, filter="data")
    with engine_for(db_settings).connect() as connection:
        schema = connection.scalar(text("SELECT current_schema()"))
    assert schema.startswith("test_") and len(schema) == 37
    engine_for(db_settings).dispose()
    admin = create_engine(db_settings.database_url, isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    admin.dispose()
    subprocess.run(
        [
            "pg_restore",
            "--no-owner",
            "--no-acl",
            "--exit-on-error",
            "--dbname",
            pg_environment(db_settings)["PGDATABASE"],
            str(restored / "database.dump"),
        ],
        env=pg_environment(db_settings),
        check=True,
        capture_output=True,
    )
    with connect(db_settings) as db:
        assert db.get(User, 1).name == "Jaime"
        assert db.get(LoginSession, "old-session") is None
        assert db.get(Photo, photo["id"]).filename == "test.jpg"
    assert (restored / "originals" / f"{photo['id']}.jpg").read_bytes() == original
