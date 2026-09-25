import pytest
from PIL import Image

from backend.geography import gps_coordinates


@pytest.mark.parametrize(
    ("latitude_ref", "longitude_ref", "expected"),
    [("N", "W", (43.25, -2.9)), (b"S", b"E", (-43.25, 2.9))],
)
def test_gps_hemispheres(latitude_ref, longitude_ref, expected):
    exif = Image.Exif()
    exif[0x8825] = {1: latitude_ref, 2: (43, 15, 0), 3: longitude_ref, 4: (2, 54, 0)}
    assert gps_coordinates(exif) == pytest.approx(expected)


@pytest.mark.parametrize("degrees", [91, -1, float("nan"), float("inf")])
def test_malformed_gps_is_ignored(degrees):
    exif = Image.Exif()
    exif[0x8825] = {1: "N", 2: (degrees, 0, 0), 3: "E", 4: (0, 0, 0)}
    assert gps_coordinates(exif) == (None, None)


def test_missing_gps_and_zero_coordinates():
    exif = Image.Exif()
    assert gps_coordinates(exif) == (None, None)
    exif[0x8825] = {1: "N", 2: (0, 0, 0), 3: "E", 4: (0, 0, 0)}
    assert gps_coordinates(exif) == (0, 0)
