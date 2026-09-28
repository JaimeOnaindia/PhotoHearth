import gzip
import zipfile

import pytest
from sqlalchemy import func, select

from backend.config import Settings
from backend.db import connect, engine_for
from backend.gazetteer import import_catalog
from backend.models import Country, Locality


def catalog(path, rows):
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("countries.tsv", "ES\tSpain\n")
        archive.writestr("localities.tsv.gz", gzip.compress(rows.encode("utf-8")))


def test_catalog_replacement_is_atomic(db_settings, tmp_path):
    source = tmp_path / "catalog.zip"
    catalog(source, "1\tLa Antilla\t37.21\t-7.22\tPPL\tES\t51\tH\t1000\n")
    assert import_catalog(db_settings, source) == 1
    with connect(db_settings) as db:
        assert db.get(Locality, 1).name == "La Antilla"
        assert db.get(Country, "ES").name == "Spain"

    catalog(source, "2\tIslantilla\t37.2\t-7.25\tPPL\tES\t51\tH\t1000\n")
    assert import_catalog(db_settings, source) == 1
    with connect(db_settings) as db:
        assert db.get(Locality, 1) is None
        assert db.get(Locality, 2).name == "Islantilla"

    catalog(source, "3\tRota\t36.6\t-6.3\tPPL\tES\t51\tCA\t1000\nmalformed\n")
    with pytest.raises(ValueError, match="9 columnas"):
        import_catalog(db_settings, source)
    with connect(db_settings) as db:
        assert db.get(Locality, 2).name == "Islantilla"
        assert db.scalar(select(func.count()).select_from(Locality)) == 1


def test_bundled_catalog_includes_example_coastal_towns(tmp_path):
    settings = Settings(data_dir=tmp_path)
    try:
        assert import_catalog(settings) > 200_000
        with connect(settings) as db:
            names = db.scalars(
                select(Locality.name).where(Locality.name.in_(["Islantilla", "La Antilla"]))
            ).all()
        assert set(names) == {"Islantilla", "La Antilla"}
    finally:
        engine_for(settings).dispose()
