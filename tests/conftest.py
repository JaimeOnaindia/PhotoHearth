import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from backend.config import Settings
from backend.db import engine_for


@pytest.fixture(params=["sqlite", "postgresql"])
def db_settings(request, tmp_path):
    """Each PostgreSQL test gets its own schema, never a production database."""
    if request.param == "sqlite":
        settings = Settings(data_dir=tmp_path, database_url=None)
        yield settings
        engine_for(settings).dispose()
        return
    url = os.getenv("PHOTOHEARTH_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set PHOTOHEARTH_TEST_DATABASE_URL to run PostgreSQL integration tests")
    schema = "test_" + uuid4().hex
    admin = create_engine(url, isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    test_url = make_url(url).update_query_dict({"options": f"-csearch_path={schema}"})
    settings = Settings(
        data_dir=tmp_path, database_url=test_url.render_as_string(hide_password=False)
    )
    try:
        yield settings
    finally:
        engine_for(settings).dispose()
        with admin.connect() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()
