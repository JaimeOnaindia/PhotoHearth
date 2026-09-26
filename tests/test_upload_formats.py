import io
from concurrent.futures import ThreadPoolExecutor

from PIL import Image

from tests.test_api import client as client
from tests.test_api import logged as logged


def test_multi_picture_jpeg_preserves_original_and_uses_primary_image(logged):
    buffer = io.BytesIO()
    primary = Image.new("RGB", (120, 80), "coral")
    secondary = Image.new("RGB", (40, 30), "blue")
    primary.save(buffer, "MPO", save_all=True, append_images=[secondary])
    payload = buffer.getvalue()
    with Image.open(io.BytesIO(payload)) as image:
        assert image.format == "MPO" and image.n_frames == 2
    response = logged.post("/api/photos/upload?filename=IMG_5589.jpeg", content=payload)
    assert response.status_code == 201, response.text
    photo = response.json()["photo"]
    assert (photo["width"], photo["height"]) == (120, 80)
    original = logged.get(f"/api/photos/{photo['id']}/file?variant=original")
    assert original.content == payload
    assert original.headers["content-type"] == "image/jpeg"
    preview = logged.get(f"/api/photos/{photo['id']}/file?variant=preview")
    with Image.open(io.BytesIO(preview.content)) as image:
        assert image.size == (120, 80) and not image.getexif()
    duplicate = logged.post("/api/photos/upload?filename=IMG_5589.jpeg", content=payload)
    assert duplicate.status_code == 201 and duplicate.json()["duplicate"]


def test_thousand_distinct_photos_with_two_concurrent_uploads(logged):
    def send(index):
        buffer = io.BytesIO()
        exif = Image.Exif()
        exif[270] = f"synthetic-batch-{index}"
        Image.new("RGB", (80, 60), "coral").save(buffer, "JPEG", exif=exif)
        response = logged.post(
            "/api/photos/upload",
            params={"filename": f"batch-{index}.jpeg"},
            content=buffer.getvalue(),
        )
        assert response.status_code == 201, response.text
        assert response.json()["duplicate"] is False
        return response.json()["photo"]["id"]

    with ThreadPoolExecutor(max_workers=2) as executor:
        identifiers = list(executor.map(send, range(1000)))
    assert len(set(identifiers)) == 1000
    assert logged.get("/api/photos").json()["total"] == 1000
    data = logged.app.state.settings.data_dir
    assert len(list((data / "originals").iterdir())) == 1000
    assert len(list((data / "previews").iterdir())) == 2000
    assert not list((data / "incoming").iterdir())
