from dataclasses import replace

import pytest
from PIL import Image
from sqlalchemy import select

from backend.db import connect, engine_for, initialize
from backend.importer import (
    ImportProblem,
    control_import_job,
    create_import_job,
    drain_imports,
    import_job,
    recover_imports,
)
from backend.models import ImportItem, ImportJob


@pytest.fixture
def import_settings(db_settings, tmp_path):
    source = tmp_path / "import-source"
    source.mkdir()
    settings = replace(
        db_settings,
        import_dir=source,
        max_upload=2 * 1024 * 1024,
    )
    initialize(settings)
    try:
        yield settings
    finally:
        engine_for(settings).dispose()


def save_image(path, color, image_format="JPEG"):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (48, 32), color).save(path, image_format)


def test_import_can_pause_resume_and_deduplicate_without_touching_source(import_settings):
    source = import_settings.import_dir
    first = source / "viaje" / "uno.jpg"
    second = source / "viaje" / "anidadas" / "dos.png"
    save_image(first, "coral")
    save_image(second, "blue", "PNG")
    original_bytes = {first: first.read_bytes(), second: second.read_bytes()}
    (source / "viaje" / "ignorar.txt").write_text("no es una foto")
    (source / "viaje" / "enlace.jpg").symlink_to(first)
    (source / "viaje" / "carpeta-enlace").symlink_to(
        source / "viaje" / "anidadas", target_is_directory=True
    )

    created = create_import_job(import_settings, "viaje")
    assert created["status"] == "queued"
    assert created["total"] == 2

    paused = control_import_job(import_settings, created["id"], "pause")
    assert paused["status"] == "paused"
    assert drain_imports(import_settings) == 0

    resumed = control_import_job(import_settings, created["id"], "resume")
    assert resumed["status"] == "queued"
    assert drain_imports(import_settings) == 2
    completed = import_job(import_settings, created["id"])
    assert completed["status"] == "completed"
    assert completed["imported"] == 2
    assert completed["failed"] == 0
    assert {path: path.read_bytes() for path in original_bytes} == original_bytes

    duplicate_job = create_import_job(import_settings, "viaje")
    assert drain_imports(import_settings) == 2
    duplicate_job = import_job(import_settings, duplicate_job["id"])
    assert duplicate_job["status"] == "completed"
    assert duplicate_job["duplicates"] == 2
    assert duplicate_job["imported"] == 0


def test_failed_file_can_be_repaired_and_retried(import_settings):
    source = import_settings.import_dir / "reparable.jpg"
    source.write_bytes(b"not-an-image")
    created = create_import_job(import_settings)

    assert drain_imports(import_settings) == 1
    failed = import_job(import_settings, created["id"])
    assert failed["status"] == "completed_errors"
    assert failed["failed"] == 1

    save_image(source, "green")
    retried = control_import_job(import_settings, created["id"], "retry")
    assert retried["status"] == "queued"
    assert retried["pending"] == 1
    assert drain_imports(import_settings) == 1
    completed = import_job(import_settings, created["id"])
    assert completed["status"] == "completed"
    assert completed["imported"] == 1
    with connect(import_settings) as db:
        item = db.scalar(select(ImportItem).where(ImportItem.job_id == created["id"]))
        assert item.attempts == 2
        assert item.error is None


def test_recovery_requeues_interrupted_work_and_cleans_only_import_temps(import_settings):
    save_image(import_settings.import_dir / "pendiente.jpg", "purple")
    created = create_import_job(import_settings)
    with connect(import_settings) as db:
        job = db.get(ImportJob, created["id"])
        item = db.scalar(select(ImportItem).where(ImportItem.job_id == created["id"]))
        job.status = "running"
        item.status = "running"
        item.attempts = 1

    stale = import_settings.data_dir / "incoming" / "import-interrumpido"
    unrelated = import_settings.data_dir / "incoming" / "upload-conservar"
    stale.write_bytes(b"partial")
    unrelated.write_bytes(b"partial")

    assert recover_imports(import_settings) == 1
    recovered = import_job(import_settings, created["id"])
    assert recovered["status"] == "queued"
    assert recovered["pending"] == 1
    assert not stale.exists()
    assert unrelated.exists()
    assert drain_imports(import_settings) == 1
    assert import_job(import_settings, created["id"])["status"] == "completed"


def test_import_rejects_paths_outside_root_and_enforces_scan_limit(import_settings, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    with pytest.raises(ImportProblem):
        create_import_job(import_settings, "../outside")
    with pytest.raises(ImportProblem):
        create_import_job(import_settings, str(outside))

    for number in range(3):
        (import_settings.import_dir / f"{number}.jpg").write_bytes(b"scan-only")
    limited = replace(import_settings, import_max_files=2)
    with pytest.raises(ImportProblem, match="límite de 2"):
        create_import_job(limited)
    with connect(import_settings) as db:
        assert db.scalar(select(ImportJob)) is None


def test_import_enqueues_more_than_one_database_batch(import_settings):
    for number in range(1_005):
        (import_settings.import_dir / f"foto-{number:04}.jpg").write_bytes(b"queued")
    created = create_import_job(import_settings)
    assert created["total"] == 1_005
    assert created["pending"] == 1_005

    canceled = control_import_job(import_settings, created["id"], "cancel")
    assert canceled["status"] == "canceled"
    assert canceled["canceled"] == 1_005
