import time
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend.auth import hasher
from backend.db import connect, engine_for
from backend.main import create_app
from backend.models import User

PASSWORD = "an-import-test-password"


@pytest.fixture
def import_client(db_settings, tmp_path):
    source = tmp_path / "server-imports"
    source.mkdir()
    settings = replace(
        db_settings,
        import_dir=source,
        web_dir=tmp_path / "missing-web",
        secure_cookie=False,
        origins=("http://testserver",),
    )
    with TestClient(create_app(settings)) as client:
        with connect(settings) as db:
            db.add(User(id=1, name="Jaime", password_hash=hasher.hash(PASSWORD)))
        yield client, settings
    engine_for(settings).dispose()


def login(client: TestClient) -> None:
    response = client.post("/api/auth/login", json={"password": PASSWORD})
    assert response.status_code == 200
    client.headers["X-CSRF-Token"] = response.json()["csrf"]


def wait_for_status(client: TestClient, job_id: str, expected: str) -> dict:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        response = client.get(f"/api/imports/{job_id}")
        assert response.status_code == 200
        job = response.json()
        if job["status"] == expected:
            return job
        time.sleep(0.02)
    pytest.fail(f"La importación {job_id} no alcanzó el estado {expected}")


def test_private_import_api_runs_persistent_job_in_background(import_client):
    client, settings = import_client
    photo = settings.import_dir / "viaje" / "foto.jpg"
    photo.parent.mkdir()
    Image.new("RGB", (64, 48), "coral").save(photo)

    assert client.get("/api/imports").status_code == 401
    login(client)
    listing = client.get("/api/imports")
    assert listing.status_code == 200
    assert listing.json() == {"enabled": True, "jobs": []}

    response = client.post("/api/imports", json={"source": "viaje"})
    assert response.status_code == 202
    created = response.json()
    assert created["total"] == 1
    completed = wait_for_status(client, created["id"], "completed")
    assert completed["imported"] == 1
    assert photo.is_file()
    assert len(client.get("/api/photos").json()["items"]) == 1

    duplicate = client.post("/api/imports", json={"source": "viaje"}).json()
    completed = wait_for_status(client, duplicate["id"], "completed")
    assert completed["duplicates"] == 1


def test_import_api_rejects_unsafe_paths_and_unknown_jobs(import_client):
    client, _ = import_client
    login(client)
    response = client.post("/api/imports", json={"source": "../private"})
    assert response.status_code == 400
    assert client.get("/api/imports/missing").status_code == 404
    assert client.post("/api/imports/missing/pause").status_code == 404
