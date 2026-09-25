import io
import sqlite3
import tarfile

from PIL import Image

from backend.backup import export
from backend.config import Settings
from backend.db import connect, initialize
from backend.media import ingest
from backend.models import LoginSession, User


def test_backup_can_restore_database_and_original(tmp_path):
    settings = Settings(data_dir=tmp_path / "source")
    initialize(settings)
    with connect(settings) as db:
        db.add(User(id=1, name="Jaime", password_hash="test-only"))
        db.add(LoginSession(token_hash="private-session", csrf="private-csrf", expires=999))
    incoming = settings.data_dir / "incoming" / "photo.jpg"
    Image.new("RGB", (20, 20), "green").save(incoming)
    original = incoming.read_bytes()
    photo = ingest(settings, incoming, "mi foto.jpg")["photo"]
    output = io.BytesIO()
    export(settings, output)
    output.seek(0)
    restored = tmp_path / "restored"
    with tarfile.open(fileobj=output) as archive:
        archive.extractall(restored, filter="data")
    with sqlite3.connect(restored / "library.sqlite3") as db:
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert db.execute("SELECT count(*) FROM sessions").fetchone()[0] == 0
        assert db.execute("SELECT filename FROM photos").fetchone()[0] == "mi foto.jpg"
    assert (restored / "originals" / f"{photo['id']}.jpg").read_bytes() == original
    initialize(Settings(data_dir=restored))
