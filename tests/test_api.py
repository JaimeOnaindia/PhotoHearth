import io
import time

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import update

from backend.auth import COOKIE, hasher
from backend.config import Settings
from backend.db import connect
from backend.main import create_app
from backend.models import LoginSession, User

PASSWORD = "a-test-password-for-my-home"


@pytest.fixture
def client(tmp_path):
    settings = Settings(
        data_dir=tmp_path,
        web_dir=tmp_path / "web",
        secure_cookie=False,
        origins=("http://testserver",),
        max_upload=1024 * 1024,
    )
    with TestClient(create_app(settings)) as client:
        with connect(settings) as db:
            db.add(User(id=1, name="Jaime", password_hash=hasher.hash(PASSWORD)))
        yield client


@pytest.fixture
def logged(client):
    response = client.post("/api/auth/login", json={"password": PASSWORD})
    assert response.status_code == 200
    client.headers["X-CSRF-Token"] = response.json()["csrf"]
    return client


def image_bytes(color="coral", format="JPEG"):
    buffer = io.BytesIO()
    Image.new("RGB", (80, 60), color).save(buffer, format=format)
    return buffer.getvalue()


def upload(client, filename="vacaciones.jpg", color="coral"):
    response = client.post(
        "/api/photos/upload", params={"filename": filename}, content=image_bytes(color)
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_private_endpoints_and_security_headers(client):
    for path in ("/api/photos", "/api/albums", "/api/stats", "/api/photos/fake/file"):
        response = client.get(path)
        assert response.status_code == 401
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["x-content-type-options"] == "nosniff"
    assert client.get("/api/health").json() == {"status": "ok"}
    assert client.get("/api/health", headers={"Host": "evil.example"}).status_code == 400


def test_session_csrf_origin_and_logout(logged):
    assert logged.get("/api/auth/me").json()["name"] == "Jaime"
    assert (
        logged.post(
            "/api/albums", json={"name": "Trip"}, headers={"X-CSRF-Token": "wrong"}
        ).status_code
        == 403
    )
    assert (
        logged.post(
            "/api/albums", json={"name": "Trip"}, headers={"Origin": "https://evil.example"}
        ).status_code
        == 403
    )
    assert logged.post("/api/auth/logout").status_code == 200
    assert logged.get("/api/auth/me").status_code == 401


def test_secure_cookie_defaults_and_expiry(client):
    client.app.state.settings = Settings(data_dir=client.app.state.settings.data_dir)
    response = client.post("/api/auth/login", json={"password": PASSWORD})
    cookie = response.headers["set-cookie"].lower()
    assert "secure" in cookie and "httponly" in cookie and "samesite=strict" in cookie
    client.cookies.set(COOKIE, response.cookies[COOKIE])
    with connect(client.app.state.settings) as db:
        db.execute(update(LoginSession).values(expires=int(time.time()) - 1))
    assert client.get("/api/auth/me").status_code == 401


def test_login_rate_limit(client):
    for _ in range(5):
        assert client.post("/api/auth/login", json={"password": "wrong"}).status_code == 401
    assert client.post("/api/auth/login", json={"password": PASSWORD}).status_code == 429


def test_photo_original_duplicate_thumbnail_and_restore(logged):
    result = upload(logged, "../../vacaciones.jpg")
    photo = result["photo"]
    assert photo["filename"] == "vacaciones.jpg"
    assert photo["width"] == 80 and photo["height"] == 60
    assert result["duplicate"] is False
    assert upload(logged)["duplicate"] is True
    assert logged.get("/api/photos").json()["total"] == 1
    original = logged.get(f"/api/photos/{photo['id']}/file?variant=original")
    assert original.content == image_bytes()
    assert "attachment" in original.headers["content-disposition"]
    thumb = logged.get(f"/api/photos/{photo['id']}/file")
    assert thumb.headers["content-type"] == "image/webp"
    assert Image.open(io.BytesIO(thumb.content)).size == (80, 60)
    assert logged.patch(f"/api/photos/{photo['id']}", json={"favorite": True}).status_code == 200
    assert logged.get("/api/photos?view=favorites").json()["total"] == 1
    logged.patch(f"/api/photos/{photo['id']}", json={"trashed": True})
    assert logged.get("/api/photos").json()["total"] == 0
    assert logged.get("/api/photos?view=trash").json()["total"] == 1
    assert upload(logged)["photo"]["deleted_at"] is not None
    logged.patch(f"/api/photos/{photo['id']}", json={"trashed": False})
    assert logged.get("/api/photos").json()["total"] == 1
    assert not list((logged.app.state.settings.data_dir / "incoming").iterdir())


def test_invalid_uploads_do_not_leave_files(logged):
    assert (
        logged.post(
            "/api/photos/upload?filename=attack.svg", content=b'<svg onload="alert(1)"></svg>'
        ).status_code
        == 415
    )
    assert logged.post("/api/photos/upload?filename=empty.jpg", content=b"").status_code == 400
    assert (
        logged.post(
            "/api/photos/upload?filename=large.jpg", content=b"a" * (1024 * 1024 + 1)
        ).status_code
        == 413
    )
    assert logged.get("/api/photos").json()["total"] == 0
    for folder in ("incoming", "originals", "previews"):
        assert not list((logged.app.state.settings.data_dir / folder).iterdir())


def test_albums_search_pagination_and_trash_counts(logged):
    first = upload(logged)["photo"]["id"]
    upload(logged, "familia.png", "blue")
    assert logged.get("/api/photos?q=vacaciones").json()["total"] == 1
    page1 = logged.get("/api/photos?limit=1").json()
    page2 = logged.get("/api/photos?limit=1&offset=1").json()
    assert page1["total"] == 2 and page1["items"][0]["id"] != page2["items"][0]["id"]
    assert logged.post("/api/albums", json={"name": "   "}).status_code == 422
    album = logged.post("/api/albums", json={"name": "Verano"}).json()["id"]
    for _ in range(2):
        assert logged.put(f"/api/albums/{album}/photos/{first}").status_code == 200
    assert logged.get(f"/api/photos?album={album}").json()["total"] == 1
    assert logged.get("/api/albums").json()[0]["count"] == 1
    logged.patch(f"/api/photos/{first}", json={"trashed": True})
    assert logged.get("/api/albums").json()[0]["count"] == 0
    assert logged.get("/api/albums").json()[0]["cover"] is None
    stats = logged.get("/api/stats").json()
    assert stats["photos"] == 1 and stats["trash"] == 1 and stats["original_bytes"] > 0
    logged.patch(f"/api/photos/{first}", json={"trashed": False})
    logged.delete(f"/api/albums/{album}/photos/{first}")
    assert logged.get(f"/api/photos?album={album}").json()["total"] == 0
    assert logged.get("/api/photos").json()["total"] == 2


def test_heic_support_and_exif_orientation(logged):
    buffer = io.BytesIO()
    exif = Image.Exif()
    exif[274] = 6
    exif[306] = "2024:06:15 12:30:00"
    Image.new("RGB", (120, 60), "green").save(buffer, "JPEG", exif=exif)
    result = logged.post("/api/photos/upload?filename=rotated.jpg", content=buffer.getvalue())
    assert result.status_code == 201
    photo = result.json()["photo"]
    assert (photo["width"], photo["height"]) == (60, 120)
    assert photo["taken_at"] == "2024-06-15T12:30:00"
    heic = image_bytes("purple", "HEIF")
    response = logged.post("/api/photos/upload?filename=iphone.heic", content=heic)
    assert response.status_code == 201
    assert response.json()["photo"]["filename"] == "iphone.heic"
