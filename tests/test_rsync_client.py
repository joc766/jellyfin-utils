from pathlib import Path

import boto3
import pytest
from botocore import UNSIGNED
from botocore.config import Config
from rich.console import Console

from media_tools.rsync_tool import RsyncClient


def get_large_test_file():
    cache_dir = Path(".pytest_cache/large-files")
    cache_dir.mkdir(parents=True, exist_ok=True)

    local_file = cache_dir / "test-small-mkv.mkv"

    if not local_file.exists():
        s3 = boto3.client("s3", config=Config(signature_version=UNSIGNED))
        s3.download_file(
            Bucket="jellyfin-utils-sample-files-195008820293-us-east-1-an",
            Key="test-small-mkv.mkv",
            Filename=str(local_file),
        )

    return local_file


def test_sync(tmp_path: Path):
    local_base = tmp_path / "mock_local"
    remote_base = tmp_path / "mock_remote"
    test_folder = local_base / "raw" / "movie" / "test_movie"
    test_folder.mkdir(parents=True)
    raw_test_file = get_large_test_file()
    test_file = raw_test_file.copy_into(test_folder)

    assert test_file.stat().st_size == 22801545

    remote_raw_movie_folder = remote_base / "raw" / "movie"
    remote_raw_movie_folder.mkdir(parents=True)
    client = RsyncClient(
        jellyfin_base=remote_base,
        jellyfin_host=None,
        jellyfin_user=None,
        local_base=local_base,
        console=Console(),
        direction="upload",
        content_format="raw",
        content_type="movie",
    )
    _ = list(client.sync_subdir("test_movie"))
    result_path = remote_raw_movie_folder / "test_movie" / "test-small-mkv.mkv"

    assert result_path.parent.is_dir()
    assert result_path.is_file()
    assert result_path.stat().st_size == 22801545
    assert result_path.stat().st_mtime == test_file.stat().st_mtime


def test_interrupt_sync(tmp_path):
    local_base = tmp_path / "mock_local"
    remote_base = tmp_path / "mock_remote"
    test_folder = local_base / "raw" / "movie" / "test_movie"
    test_folder.mkdir(parents=True)
    raw_test_file = get_large_test_file()
    test_file = raw_test_file.copy_into(test_folder)

    assert test_file.stat().st_size == 22801545

    remote_raw_movie_folder = remote_base / "raw" / "movie"
    remote_raw_movie_folder.mkdir(parents=True)
    client = RsyncClient(
        jellyfin_base=remote_base,
        jellyfin_host=None,
        jellyfin_user=None,
        local_base=local_base,
        console=Console(),
        direction="upload",
        content_format="raw",
        content_type="movie",
    )
    with pytest.raises(InterruptedError):
        generator = client.sync_subdir("test_movie")
        next(generator)
        generator.throw(KeyboardInterrupt)

    assert client.rsync_proc is not None
    assert client.rsync_proc.returncode == 20
