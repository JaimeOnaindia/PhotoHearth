from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session

from backend.config import Settings


@lru_cache(maxsize=16)
def engine_for(settings: Settings):
    url = settings.database_url or URL.create("sqlite", database=str(settings.database))
    sqlite = str(url).startswith("sqlite")
    engine = create_engine(
        url,
        connect_args={"check_same_thread": False, "timeout": 15} if sqlite else {},
        pool_size=3,
        max_overflow=2,
        pool_pre_ping=True,
        hide_parameters=True,
    )

    def configure_sqlite(connection, _):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=15000")
        cursor.close()

    if sqlite:
        event.listen(engine, "connect", configure_sqlite)
    return engine


def lock_auth(db: Session) -> None:
    """Serialize authentication writes without serializing photo inserts."""
    if db.bind.dialect.name == "sqlite":
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")
    else:
        db.execute(text("SELECT pg_advisory_xact_lock(706804101)"))


@contextmanager
def connect(settings: Settings):
    with Session(engine_for(settings), expire_on_commit=False) as session, session.begin():
        yield session


def initialize(settings: Settings) -> None:
    settings.prepare()
    engine = engine_for(settings)
    if engine.dialect.name == "sqlite":
        with engine.connect() as connection:
            connection.exec_driver_sql("PRAGMA journal_mode=WAL")
    config = Config(str(Path(__file__).resolve().parent.parent / "alembic.ini"))
    with engine.begin() as connection:
        if engine.dialect.name == "postgresql":
            connection.execute(text("SELECT pg_advisory_xact_lock(706804102)"))
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
