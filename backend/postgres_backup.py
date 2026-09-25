"""PostgreSQL snapshots using the matching pg_dump client, without credentials in argv."""

import os
import subprocess
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.engine import make_url

from backend.config import Settings
from backend.db import engine_for
from backend.models import Photo


def pg_environment(settings: Settings) -> dict[str, str]:
    url = make_url(settings.database_url)
    environment = os.environ.copy()
    environment.update(
        {
            "PGHOST": url.host or "localhost",
            "PGPORT": str(url.port or 5432),
            "PGDATABASE": url.database or "photohearth",
            "PGUSER": url.username or "photohearth",
            "PGPASSWORD": url.password or "",
            "PGOPTIONS": str(url.query.get("options", "")),
        }
    )
    return environment


def snapshot(settings: Settings, target: Path) -> list[tuple[str, str]]:
    engine = engine_for(settings)
    with engine.connect().execution_options(isolation_level="REPEATABLE READ") as connection:
        with connection.begin():
            snapshot_id = connection.scalar(text("SELECT pg_export_snapshot()"))
            schema = connection.scalar(text("SELECT current_schema()"))
            photos = connection.execute(select(Photo.id, Photo.extension)).all()
            subprocess.run(
                [
                    "pg_dump",
                    "--format=custom",
                    "--no-owner",
                    "--no-acl",
                    f"--snapshot={snapshot_id}",
                    f"--schema={schema}",
                    "--exclude-table-data=*.sessions",
                    "--exclude-table-data=*.login_attempts",
                    "--file",
                    str(target),
                ],
                env=pg_environment(settings),
                check=True,
                capture_output=True,
            )
    return [(row.id, row.extension) for row in photos]
