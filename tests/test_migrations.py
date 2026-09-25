from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from backend.db import connect, engine_for, initialize
from backend.models import User


def test_upgrade_is_idempotent_and_models_match(db_settings):
    settings = db_settings
    initialize(settings)
    with connect(settings) as db:
        db.add(User(id=1, name="Preservar", password_hash="test-only"))
    initialize(settings)
    with connect(settings) as db:
        assert db.get(User, 1).name == "Preservar"
    config = Config("alembic.ini")
    with engine_for(settings).begin() as connection:
        config.attributes["connection"] = connection
        command.check(config)
    assert "alembic_version" in inspect(engine_for(settings)).get_table_names()


def test_migration_roundtrip_on_empty_database(db_settings):
    settings = db_settings
    initialize(settings)
    config = Config("alembic.ini")
    with engine_for(settings).begin() as connection:
        config.attributes["connection"] = connection
        command.downgrade(config, "base")
        command.upgrade(config, "head")
        command.check(config)


def test_location_migration_preserves_existing_album_membership(db_settings):
    db_settings.prepare()
    config = Config("alembic.ini")
    with engine_for(db_settings).begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "97e1eb47e302")
        connection.execute(
            text(
                "INSERT INTO photos (id, sha256, filename, extension, mime, bytes, width, "
                "height, taken_at, uploaded_at) VALUES "
                "('photo', 'hash', 'photo.jpg', 'jpg', 'image/jpeg', 10, 1, 1, '2026', '2026')"
            )
        )
        connection.execute(
            text("INSERT INTO albums (id, name, created_at) VALUES ('album', 'Viaje', '2026')")
        )
        connection.execute(
            text("INSERT INTO album_photos (album_id, photo_id) VALUES ('album', 'photo')")
        )
        command.upgrade(config, "head")
        assert connection.scalar(text("SELECT COUNT(*) FROM album_photos")) == 1
        command.downgrade(config, "97e1eb47e302")
        assert connection.scalar(text("SELECT COUNT(*) FROM album_photos")) == 1
