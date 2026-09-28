import io
from concurrent.futures import ThreadPoolExecutor

import pytest
from PIL import Image
from PIL.TiffImagePlugin import IFDRational

from backend.db import connect
from backend.models import Country, Locality
from tests.test_api import client as client
from tests.test_api import logged as logged
from tests.test_api import upload


def test_places_are_private(client):
    assert client.get("/api/places").status_code == 401


def test_missing_photos_include_album_memberships_for_grouping(logged):
    first = upload(logged, color="coral")["photo"]["id"]
    second = upload(logged, color="blue")["photo"]["id"]
    other = upload(logged, color="green")["photo"]["id"]
    album = logged.post("/api/albums", json={"name": "Portugal"}).json()["id"]
    for photo_id in (first, second):
        assert logged.put(f"/api/albums/{album}/photos/{photo_id}").status_code == 200

    items = logged.get("/api/photos", params={"location": "missing"}).json()["items"]
    memberships = {item["id"]: item["albums"] for item in items}
    assert memberships == {
        first: [{"id": album, "name": "Portugal"}],
        second: [{"id": album, "name": "Portugal"}],
        other: [],
    }
    assert "albums" not in logged.get("/api/photos").json()["items"][0]


def test_places_use_nearby_locality_but_keep_manual_names(logged):
    with connect(logged.app.state.settings) as db:
        db.add(Country(code="ES", name="Spain"))
        db.flush()
        db.add_all(
            [
                Locality(
                    geoname_id=1, name="Islantilla", latitude=37.20572, longitude=-7.23742,
                    feature_code="PPL", country_code="ES", population=1261,
                ),
                Locality(
                    geoname_id=2, name="La Antilla", latitude=37.20709, longitude=-7.20909,
                    feature_code="PPL", country_code="ES", population=3500,
                ),
            ]
        )
    first = upload(logged, color="coral")["photo"]["id"]
    second = upload(logged, color="blue")["photo"]["id"]
    for photo_id, longitude in ((first, -7.257), (second, -7.216)):
        assert logged.patch(
            f"/api/photos/{photo_id}",
            json={"location": {"latitude": 37.203, "longitude": longitude, "name": ""}},
        ).status_code == 200
    places = logged.get("/api/places").json()["items"]
    assert {place["nearby_name"] for place in places} == {"Islantilla", "La Antilla"}
    assert all(place["name"] is None for place in places)

    assert logged.patch(
        f"/api/photos/{first}",
        json={"location": {"latitude": 37.203, "longitude": -7.257, "name": "Nuestra playa"}},
    ).status_code == 200
    places = logged.get("/api/places").json()["items"]
    named = next(place for place in places if place["longitude"] == pytest.approx(-7.257))
    assert named["name"] == "Nuestra playa"
    assert named["nearby_name"] is None


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
    assert places["items"][0]["nearby_name"] is None
    assert logged.get("/api/photos?q=%").json()["total"] == 0


def test_location_filters_and_transactional_batch_updates(logged):
    first = upload(logged, "primera.jpg", "coral")["photo"]["id"]
    second = upload(logged, "segunda.jpg", "blue")["photo"]["id"]

    assert logged.get("/api/photos", params={"location": "missing"}).json()["total"] == 2
    assert logged.get("/api/photos", params={"location": "located"}).json()["total"] == 0

    response = logged.patch(
        "/api/photos/batch",
        json={
            "ids": [first, second, first],
            "location": {"latitude": 43.263, "longitude": -2.935, "name": " Bilbao "},
        },
    )
    assert response.status_code == 200 and response.json() == {"updated": 2}
    assert logged.get("/api/photos", params={"location": "missing"}).json()["total"] == 0
    assert logged.get("/api/photos", params={"location": "located"}).json()["total"] == 2
    places = logged.get("/api/places").json()
    assert places["total"] == 1 and places["items"][0]["name"] == "Bilbao"
    assert logged.patch(f"/api/photos/{second}", json={"location": None}).status_code == 200
    filtered = logged.get("/api/photos", params={"place": places["items"][0]["id"]})
    assert filtered.status_code == 200 and filtered.json()["total"] == 1
    assert logged.patch(
        f"/api/photos/{second}",
        json={"location": {"latitude": 43.263, "longitude": -2.935, "name": "Bilbao"}},
    ).status_code == 200

    missing_id = "0" * 32
    failed = logged.patch(
        "/api/photos/batch",
        json={"ids": [first, missing_id], "favorite": True},
    )
    assert failed.status_code == 404
    assert logged.get("/api/photos?view=favorites").json()["total"] == 0
    assert logged.patch("/api/photos/batch", json={"ids": [first]}).status_code == 422
    assert logged.patch("/api/photos/batch", json={"ids": []}).status_code == 422

    favorite = logged.patch(
        "/api/photos/batch",
        json={"ids": [first, second], "favorite": True},
    )
    assert favorite.status_code == 200 and favorite.json() == {"updated": 2}
    assert logged.get("/api/photos?view=favorites").json()["total"] == 2


def test_concurrent_uploads_are_deduplicated(logged):
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: upload(logged), range(4)))
    assert len({result["photo"]["id"] for result in results}) == 1
    assert sum(not result["duplicate"] for result in results) == 1
    assert logged.get("/api/photos").json()["total"] == 1
