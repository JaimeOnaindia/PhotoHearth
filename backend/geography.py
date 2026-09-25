import math


def gps_coordinates(exif) -> tuple[float | None, float | None]:
    """Read EXIF GPS without network lookups; ignore incomplete or malformed tags."""
    try:
        gps = exif.get(0x8825)
        if not isinstance(gps, dict):
            gps = exif.get_ifd(0x8825)

        def coordinate(values, reference, positive, negative, maximum):
            if isinstance(reference, bytes):
                reference = reference.decode("ascii")
            reference = reference.rstrip("\x00").upper()
            if reference not in (positive, negative) or len(values) != 3:
                raise ValueError("Invalid GPS reference")
            degrees, minutes, seconds = map(float, values)
            if not all(math.isfinite(x) for x in (degrees, minutes, seconds)):
                raise ValueError("Non-finite GPS coordinate")
            if not (0 <= degrees <= maximum and 0 <= minutes < 60 and 0 <= seconds < 60):
                raise ValueError("GPS coordinate out of range")
            result = degrees + minutes / 60 + seconds / 3600
            if result > maximum:
                raise ValueError("GPS coordinate out of range")
            return -result if reference == negative else result

        return (
            coordinate(gps[2], gps[1], "N", "S", 90),
            coordinate(gps[4], gps[3], "E", "W", 180),
        )
    except (
        ValueError,
        TypeError,
        AttributeError,
        KeyError,
        OSError,
        ZeroDivisionError,
        OverflowError,
    ):
        return None, None
