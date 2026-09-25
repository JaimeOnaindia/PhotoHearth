import os
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.engine import URL


def database_url_from_env() -> str | None:
    if os.getenv("PHOTOHEARTH_DATABASE_URL"):
        return os.environ["PHOTOHEARTH_DATABASE_URL"]
    if not os.getenv("PGHOST"):
        return None
    password_file = os.getenv("PHOTOHEARTH_DB_PASSWORD_FILE")
    password = Path(password_file).read_text().strip() if password_file else os.getenv("PGPASSWORD")
    return URL.create(
        "postgresql+psycopg",
        username=os.getenv("PGUSER", "photohearth"),
        password=password,
        host=os.environ["PGHOST"],
        port=int(os.getenv("PGPORT", "5432")),
        database=os.getenv("PGDATABASE", "photohearth"),
    ).render_as_string(hide_password=False)


@dataclass(frozen=True)
class Settings:
    data_dir: Path = field(
        default_factory=lambda: Path(os.getenv("PHOTOHEARTH_DATA", "data")).resolve()
    )
    web_dir: Path = field(default_factory=lambda: Path("dist").resolve())
    database_url: str | None = field(default_factory=database_url_from_env, repr=False)
    origins: tuple[str, ...] = field(
        default_factory=lambda: tuple(
            x.strip().rstrip("/")
            for x in os.getenv("PHOTOHEARTH_ORIGINS", "https://photos.home.arpa").split(",")
            if x.strip()
        )
    )
    secure_cookie: bool = field(
        default_factory=lambda: os.getenv("PHOTOHEARTH_SECURE_COOKIE", "true").lower() == "true"
    )
    max_upload: int = 40 * 1024 * 1024
    session_seconds: int = 7 * 24 * 60 * 60
    upload_concurrency: int = 2

    @property
    def database(self) -> Path:
        return self.data_dir / "library.sqlite3"

    def prepare(self) -> None:
        for subdirectory in ("originals", "previews", "incoming"):
            (self.data_dir / subdirectory).mkdir(parents=True, exist_ok=True, mode=0o700)
