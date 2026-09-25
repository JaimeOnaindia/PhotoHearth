import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    data_dir: Path = field(
        default_factory=lambda: Path(os.getenv("PHOTOHEARTH_DATA", "data")).resolve()
    )
    web_dir: Path = field(default_factory=lambda: Path("dist").resolve())
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

    @property
    def database(self) -> Path:
        return self.data_dir / "library.sqlite3"

    def prepare(self) -> None:
        for subdirectory in ("originals", "previews", "incoming"):
            (self.data_dir / subdirectory).mkdir(parents=True, exist_ok=True, mode=0o700)
