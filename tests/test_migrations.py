from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from backend.config import Settings
from backend.db import connect, engine_for, initialize
from backend.models import User


def test_upgrade_is_idempotent_and_models_match(tmp_path):
    settings = Settings(data_dir=tmp_path)
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


def test_migration_roundtrip_on_empty_database(tmp_path):
    settings = Settings(data_dir=tmp_path)
    initialize(settings)
    config = Config("alembic.ini")
    with engine_for(settings).begin() as connection:
        config.attributes["connection"] = connection
        command.downgrade(config, "base")
        command.upgrade(config, "head")
        command.check(config)
