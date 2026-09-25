import asyncio
import shutil
from contextlib import asynccontextmanager
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import case, func, select
from starlette.middleware.trustedhost import TrustedHostMiddleware

from backend import albums, auth, photos
from backend.config import Settings
from backend.db import connect, initialize
from backend.models import Album, Photo


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        initialize(settings)
        app.state.upload_lock = asyncio.Semaphore(1)
        yield

    app = FastAPI(title="PhotoHearth", lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.settings = settings
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=list({urlparse(origin).hostname for origin in settings.origins})
        + ["localhost", "127.0.0.1", "testserver"],
    )

    @app.middleware("http")
    async def security(request: Request, call_next):
        origin = request.headers.get("origin")
        if (
            request.method not in {"GET", "HEAD", "OPTIONS"}
            and origin
            and origin not in settings.origins
        ):
            return JSONResponse({"detail": "Origen no permitido."}, status_code=403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' blob: data:; style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; connect-src 'self'; font-src 'self'; object-src 'none'; "
            "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        if settings.secure_cookie:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

    app.include_router(auth.router)
    app.include_router(photos.router)
    app.include_router(albums.router)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/stats", dependencies=[Depends(auth.session)])
    def stats():
        with connect(settings) as db:
            totals = (
                db.execute(
                    select(
                        func.count(case((Photo.deleted_at.is_(None), 1))).label("photos"),
                        func.count(
                            case((Photo.deleted_at.is_(None) & Photo.favorite.is_(True), 1))
                        ).label("favorites"),
                        func.count(case((Photo.deleted_at.is_not(None), 1))).label("trash"),
                        func.coalesce(func.sum(Photo.bytes), 0).label("original_bytes"),
                    )
                )
                .mappings()
                .one()
            )
            album_count = db.scalar(select(func.count()).select_from(Album))
        disk = shutil.disk_usage(settings.data_dir)
        return {
            **dict(totals),
            "albums": album_count,
            "disk_total": disk.total,
            "disk_free": disk.free,
            "max_upload": settings.max_upload,
        }

    if settings.web_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=settings.web_dir / "assets"), name="assets")

        @app.get("/{path:path}")
        def frontend(path: str):
            if path.startswith("api/"):
                return JSONResponse({"detail": "Ruta no encontrada."}, status_code=404)
            public = {"manifest.webmanifest", "icon.svg", "sw.js"}
            target = settings.web_dir / (path if path in public else "index.html")
            return FileResponse(target, headers={"Cache-Control": "no-cache"})

    return app


app = create_app()
