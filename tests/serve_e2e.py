"""Isolated browser-test server. Never reads or changes the user's library."""

from pathlib import Path
from tempfile import TemporaryDirectory

import uvicorn
from PIL import Image, ImageDraw

from backend.auth import hasher
from backend.config import Settings
from backend.db import connect, initialize
from backend.main import create_app
from backend.models import User


def main():
    fixtures = Path("test-results/fixtures")
    fixtures.mkdir(parents=True, exist_ok=True)
    palettes = [("#d7daca", "#738776"), ("#e7c4a1", "#b47f59"), ("#b8cdd0", "#4a777e")]
    for i in range(12):
        sky, mountain = palettes[i % len(palettes)]
        image = Image.new("RGB", (800, 650), sky)
        draw = ImageDraw.Draw(image)
        draw.ellipse((520 - i * 9, 70, 615 - i * 9, 165), fill="#f4e8c5")
        draw.polygon(
            [
                (0, 520),
                (260, 140 + i * 10),
                (530, 520),
                (700, 320),
                (800, 500),
                (800, 650),
                (0, 650),
            ],
            fill=mountain,
        )
        image.save(fixtures / f"recuerdo-{i + 1:02}.jpg", "JPEG")
    with TemporaryDirectory(prefix="photohearth-e2e-") as directory:
        settings = Settings(
            data_dir=Path(directory), secure_cookie=False, origins=("http://127.0.0.1:8765",)
        )
        initialize(settings)
        with connect(settings) as db:
            db.add(
                User(
                    id=1, name="Jaime", password_hash=hasher.hash("photohearth-test-only-password")
                )
            )
        uvicorn.run(
            create_app(settings),
            host="127.0.0.1",
            port=8765,
            proxy_headers=False,
            log_level="warning",
        )


if __name__ == "__main__":
    main()
