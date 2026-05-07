from pathlib import Path

import pytest

from media_tools.ffmpeg_tool import compress_mkv


def test_file_exists(tmp_path: Path):
    with pytest.raises(FileExistsError):
        dummy_input = tmp_path / "input.mkv"
        dummy_input.touch()
        test_path = tmp_path / "existing_file.mp4"
        test_path.touch()
        compress_mkv(dummy_input, output=test_path, overwrite=False)


def test_file_not_exists(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        dummy_input = tmp_path / "input.mkv"
        test_path = tmp_path / "existing_file.mp4"
        compress_mkv(dummy_input, output=test_path, overwrite=False)
