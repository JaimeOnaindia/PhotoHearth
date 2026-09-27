from typing import Literal

import anyio
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from backend.auth import session
from backend.importer import (
    ImportNotFound,
    ImportProblem,
    ImportUnavailable,
    control_import_job,
    create_import_job,
    import_job,
    list_import_jobs,
)

router = APIRouter(prefix="/api/imports", dependencies=[Depends(session)], tags=["imports"])


class ImportInput(BaseModel):
    source: str = Field(default=".", max_length=1024)

    @field_validator("source")
    @classmethod
    def normalize_source(cls, value: str) -> str:
        return value.strip() or "."


def _http_error(error: ImportProblem) -> HTTPException:
    if isinstance(error, ImportNotFound):
        return HTTPException(404, str(error))
    if isinstance(error, ImportUnavailable):
        return HTTPException(503, str(error))
    return HTTPException(400, str(error))


@router.get("")
async def imports(request: Request):
    settings = request.app.state.settings
    jobs = await anyio.to_thread.run_sync(list_import_jobs, settings)
    return {"enabled": settings.import_dir is not None, "jobs": jobs}


@router.get("/{job_id}")
async def import_detail(job_id: str, request: Request):
    try:
        return await anyio.to_thread.run_sync(
            import_job, request.app.state.settings, job_id
        )
    except ImportProblem as error:
        raise _http_error(error) from error


@router.post("", status_code=202)
async def create_import(body: ImportInput, request: Request):
    try:
        job = await anyio.to_thread.run_sync(
            create_import_job, request.app.state.settings, body.source
        )
    except ImportProblem as error:
        raise _http_error(error) from error
    request.app.state.import_wakeup.set()
    return job


@router.post("/{job_id}/{action}")
async def control_import(
    job_id: str,
    action: Literal["pause", "resume", "retry", "cancel"],
    request: Request,
):
    try:
        job = await anyio.to_thread.run_sync(
            control_import_job, request.app.state.settings, job_id, action
        )
    except ImportProblem as error:
        raise _http_error(error) from error
    if action in {"resume", "retry"}:
        request.app.state.import_wakeup.set()
    return job
