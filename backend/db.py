from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session

from backend.config import Settings


@lru_cache(maxsize=16)
def engine_for(settings: Settings):
    engine = create_engine(
        URL.create("sqlite", database=str(settings.database)),
        connect_args={"check_same_thread": False, "timeout": 15},
        pool_size=3,
        max_overflow=2,
    )

    @event.listens_for(engine, "connect")
    def configure_sqlite(connection, _):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=15000")
        cursor.close()

    return engine


@contextmanager
def connect(settings: Settings):
    with Session(engine_for(settings), expire_on_commit=False) as session, session.begin():
        yield session


def initialize(settings: Settings) -> None:
    settings.prepare()
    engine = engine_for(settings)
    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA journal_mode=WAL")
    config = Config(str(Path(__file__).resolve().parent.parent / "alembic.ini"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
