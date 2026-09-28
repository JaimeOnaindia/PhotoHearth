"""Import the bundled GeoNames catalogue into the local database.

The source and CC BY 4.0 attribution are in resources/geonames-20260928.zip.
No photo coordinates are sent to GeoNames or any other geocoding service.
"""

import argparse
import csv
import gzip
import io
import zipfile
from pathlib import Path

from sqlalchemy import delete, insert

from backend.config import Settings
from backend.db import connect, initialize
from backend.models import Country, Locality

CATALOG = Path(__file__).resolve().parent / "resources" / "geonames-20260928.zip"
BATCH_SIZE = 1000


def import_catalog(settings: Settings, source: Path = CATALOG) -> int:
    """Atomically replace the local catalogue. Existing photos are untouched."""
    initialize(settings)
    with zipfile.ZipFile(source) as archive:
        countries = [
            {"code": code, "name": name}
            for code, name in csv.reader(
                io.TextIOWrapper(archive.open("countries.tsv"), encoding="utf-8"),
                delimiter="\t",
            )
        ]
        if not countries:
            raise ValueError("El catálogo de países está vacío")
        with connect(settings) as db:
            db.execute(delete(Locality))
            db.execute(delete(Country))
            db.execute(insert(Country), countries)
            count = 0
            with gzip.open(archive.open("localities.tsv.gz"), "rt", encoding="utf-8") as data:
                batch = []
                for row in csv.reader(data, delimiter="\t"):
                    if len(row) != 9:
                        raise ValueError(f"Localidad {count + 1}: se esperaban 9 columnas")
                    (
                        geoname_id,
                        name,
                        latitude,
                        longitude,
                        feature_code,
                        country,
                        admin1,
                        admin2,
                        population,
                    ) = row
                    batch.append(
                        {
                            "geoname_id": int(geoname_id),
                            "name": name,
                            "latitude": float(latitude),
                            "longitude": float(longitude),
                            "feature_code": feature_code,
                            "country_code": country,
                            "admin1": admin1 or None,
                            "admin2": admin2 or None,
                            "population": int(population),
                        }
                    )
                    if len(batch) == BATCH_SIZE:
                        db.execute(insert(Locality), batch)
                        count += len(batch)
                        batch = []
                if batch:
                    db.execute(insert(Locality), batch)
                    count += len(batch)
            if count == 0:
                raise ValueError("El catálogo de localidades está vacío")
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Cargar catálogo geográfico local de GeoNames")
    parser.add_argument("--source", type=Path, default=CATALOG)
    args = parser.parse_args()
    count = import_catalog(Settings(), args.source)
    print(f"Importadas {count} localidades del catálogo local de GeoNames.")


if __name__ == "__main__":
    main()
