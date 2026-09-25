from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select

from backend.auth import session
from backend.db import connect
from backend.models import Photo

router = APIRouter(prefix="/api/places", dependencies=[Depends(session)], tags=["places"])


def latitude_cell():
    return func.floor((Photo.latitude + 90) * 100)


def longitude_cell():
    return func.floor((Photo.longitude + 180) * 100)


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
        items = [
            {**dict(row), "id": f"{int(row['lat_cell'])}:{int(row['lon_cell'])}"} for row in rows
        ]
    return {"items": items, "total": total, "located": located, "missing": missing}
