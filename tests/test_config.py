from pathlib import Path

import pytest

from media_tools import load_config


def test_missing_config_file(tmp_path: Path):
    # test nonexistent env file
    with pytest.raises(FileNotFoundError):
        test_config_file = tmp_path / ".env"
        load_config(test_config_file)


def test_missing_config_params(tmp_path: Path):
    # test empty config file
    with pytest.raises(RuntimeError):
        test_config_file = tmp_path / ".env"
        test_config_file.touch()
        load_config(test_config_file)


def test_valid_config_file(tmp_path: Path):
    test_config_file = tmp_path / ".env"
    test_config_file.touch()
    local_base = tmp_path / "local"
    local_base.mkdir()
    jellyfin_base = tmp_path / "remote"
    jellyfin_base.mkdir()
    test_config_file.write_text(
        f"LOCAL_BASE={tmp_path}\n"
        f"JELLYFIN_BASE={jellyfin_base}\n"
        "JELLYFIN_USER=jack\n"
        "JELLYFIN_HOST=localhost\n"
        "OMDB_API_KEY=fake-api-key\n"
    )
    load_config(test_config_file)
