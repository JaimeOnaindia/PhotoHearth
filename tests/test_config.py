from backend.config import Settings


def test_default_data_directory_lives_outside_the_repository(monkeypatch, tmp_path):
    monkeypatch.delenv("PHOTOHEARTH_DATA", raising=False)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert Settings().data_dir == tmp_path / "photohearth"


def test_explicit_data_directory_still_takes_precedence(monkeypatch, tmp_path):
    configured = tmp_path / "custom-library"
    monkeypatch.setenv("PHOTOHEARTH_DATA", str(configured))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "ignored"))
    assert Settings().data_dir == configured
