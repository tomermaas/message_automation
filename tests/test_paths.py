from pathlib import Path
from app.services import paths
from app.config import CONFIG


def test_paths_functions(tmp_path, monkeypatch):
    # Redirect data root to temporary directory
    monkeypatch.setattr(CONFIG, "data_root", str(tmp_path))

    # data_root
    assert paths.data_root() == Path(tmp_path)

    # course_dir creates directory
    cdir = paths.course_dir(123)
    assert cdir == Path(tmp_path) / "courses" / "123"
    assert cdir.exists()

    # distance_db_path and messages_db_path
    distance_path = paths.distance_db_path(123)
    messages_path = paths.messages_db_path(123)
    assert distance_path == cdir / "distance.db"
    assert messages_path == cdir / "messages.db"
