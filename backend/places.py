from math import asin, cos, radians, sin, sqrt

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.auth import session
from backend.db import connect
from backend.models import Locality, Photo

router = APIRouter(prefix="/api/places", dependencies=[Depends(session)], tags=["places"])
MAX_NEARBY_KM = 10


def nearby_locality(db: Session, latitude: float, longitude: float) -> str | None:
    """Find a nearby populated place from the local catalogue, never by external API."""
    lat_delta = MAX_NEARBY_KM / 110
    polar_latitude = min(90, abs(latitude) + lat_delta)
    longitude_scale = cos(radians(polar_latitude))
    lon_delta = MAX_NEARBY_KM / (111.32 * longitude_scale) if longitude_scale > 0 else 180
    query = select(Locality.name, Locality.latitude, Locality.longitude).where(
        Locality.latitude.between(latitude - lat_delta, latitude + lat_delta)
    )
    if lon_delta < 180:
        low, high = longitude - lon_delta, longitude + lon_delta
        if low < -180:
            query = query.where((Locality.longitude >= low + 360) | (Locality.longitude <= high))
        elif high > 180:
            query = query.where((Locality.longitude >= low) | (Locality.longitude <= high - 360))
        else:
            query = query.where(Locality.longitude.between(low, high))

    nearest_name = None
    nearest_distance = MAX_NEARBY_KM
    for name, other_lat, other_lon in db.execute(query):
        lat_difference = radians(other_lat - latitude)
        lon_difference = radians(other_lon - longitude)
        a = sin(lat_difference / 2) ** 2 + (
            cos(radians(latitude)) * cos(radians(other_lat)) * sin(lon_difference / 2) ** 2
        )
        distance = 2 * 6371.0088 * asin(min(1, sqrt(a)))
        if distance < nearest_distance:
            nearest_name, nearest_distance = name, distance
    return nearest_name


def latitude_cell():
    return func.floor(func.coalesce((Photo.latitude + 90) * 100, -1))


def longitude_cell():
    return func.floor(func.coalesce((Photo.longitude + 180) * 100, -1))


@router.get("")
def places(request: Request):
    """Group nearby photographs in 0.01-degree cells without third-party geocoding."""
    grouped = (
        select(
            latitude_cell().label("lat_cell"),
            longitude_cell().label("lon_cell"),
            func.avg(Photo.latitude).label("latitude"),
            func.avg(Photo.longitude).label("longitude"),
            func.count().label("count"),
            func.min(Photo.id).label("cover"),
            func.max(Photo.taken_at).label("last_visit"),
            func.min(Photo.location_name).label("name"),
        )
        .where(Photo.deleted_at.is_(None), Photo.latitude.is_not(None))
        .group_by("lat_cell", "lon_cell")
    )
    with connect(request.app.state.settings) as db:
        total = db.scalar(select(func.count()).select_from(grouped.subquery()))
        located = db.scalar(
            select(func.count())
            .select_from(Photo)
            .where(
                Photo.deleted_at.is_(None),
                Photo.latitude.is_not(None),
            )
        )
        missing = db.scalar(
            select(func.count())
            .select_from(Photo)
            .where(
                Photo.deleted_at.is_(None),
                Photo.latitude.is_(None),
            )
        )
        rows = db.execute(grouped.order_by(func.max(Photo.taken_at).desc()).limit(500)).mappings()
        items = []
        for row in rows:
            place = {**dict(row), "id": f"{int(row['lat_cell'])}:{int(row['lon_cell'])}"}
            place["nearby_name"] = None
            if not place["name"]:
                place["nearby_name"] = nearby_locality(db, place["latitude"], place["longitude"])
            items.append(place)
    return {"items": items, "total": total, "located": located, "missing": missing}
