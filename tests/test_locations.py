import io
from concurrent.futures import ThreadPoolExecutor

import pytest
from PIL import Image
from PIL.TiffImagePlugin import IFDRational

from tests.test_api import client as client
from tests.test_api import logged as logged
from tests.test_api import upload


def test_places_are_private(client):
    assert client.get("/api/places").status_code == 401


def test_exif_location_and_manual_updates(logged):
    buffer = io.BytesIO()
    exif = Image.Exif()
    exif[0x8825] = {
        1: "N",
        2: tuple(map(IFDRational, (43, 15, 0))),
        3: "W",
        4: tuple(map(IFDRational, (2, 54, 0))),
    }
    Image.new("RGB", (80, 60), "green").save(buffer, "JPEG", exif=exif)
    photo = logged.post(
        "/api/photos/upload?filename=bilbao.jpg",
        content=buffer.getvalue(),
    ).json()["photo"]
    assert photo["latitude"] == pytest.approx(43.25)
    assert photo["longitude"] == pytest.approx(-2.9)
    thumb = logged.get(f"/api/photos/{photo['id']}/file")
    assert not Image.open(io.BytesIO(thumb.content)).getexif()
    location = {"latitude": 43.251, "longitude": -2.901, "name": "  Bilbao  "}
    updated = logged.patch(f"/api/photos/{photo['id']}", json={"location": location})
    assert updated.status_code == 200 and updated.json()["location_name"] == "Bilbao"
    places = logged.get("/api/places").json()
    assert places["total"] == 1 and places["located"] == 1
    place = places["items"][0]
    assert place["name"] == "Bilbao" and place["count"] == 1
    assert logged.get("/api/photos", params={"place": place["id"]}).json()["total"] == 1
    logged.patch(f"/api/photos/{photo['id']}", json={"trashed": True})
    assert logged.get("/api/places").json()["items"] == []
    logged.patch(f"/api/photos/{photo['id']}", json={"trashed": False, "location": None})
    assert logged.get("/api/places").json()["missing"] == 1
    # Clearing the catalogue does not modify the original file's EXIF.
    assert (
        logged.get(f"/api/photos/{photo['id']}/file?variant=original").content == buffer.getvalue()
    )


def test_location_validation_and_grouping(logged):
    first = upload(logged)["photo"]["id"]
    second = upload(logged, color="blue")["photo"]["id"]
    for location in (
        {"latitude": 91, "longitude": 0},
        {"latitude": 2},
        {"latitude": 0, "longitude": -181},
    ):
        assert logged.patch(f"/api/photos/{first}", json={"location": location}).status_code == 422
    for photo_id in (first, second):
        assert (
            logged.patch(
                f"/api/photos/{photo_id}",
                json={
                    "location": {"latitude": 0, "longitude": 0},
                },
            ).status_code
            == 200
        )
    places = logged.get("/api/places").json()
    assert places["total"] == 1 and places["items"][0]["count"] == 2
    assert logged.get("/api/photos?q=%").json()["total"] == 0


def test_concurrent_uploads_are_deduplicated(logged):
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: upload(logged), range(4)))
    assert len({result["photo"]["id"] for result in results}) == 1
    assert sum(not result["duplicate"] for result in results) == 1
    assert logged.get("/api/photos").json()["total"] == 1
