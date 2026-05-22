from collections import deque
from pathlib import Path

import boto3
import pytest
from botocore import UNSIGNED
from botocore.config import Config

from media_tools.ffmpeg_tool import FFmpegClient


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


def test_file_exists(tmp_path: Path):
    with pytest.raises(FileExistsError):
        dummy_input = tmp_path / "input.mkv"
        dummy_input.touch()
        test_path = tmp_path / "existing_file.mp4"
        test_path.touch()
        client = FFmpegClient(input_path=dummy_input, output_path=test_path)
        # iterate through generator
        list(client.start_compress_mkv(overwrite=False))


def test_file_not_exists(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        dummy_input = tmp_path / "input.mkv"
        test_path = tmp_path / "existing_file.mp4"
        client = FFmpegClient(input_path=dummy_input, output_path=test_path)
        # iterate through generator
        list(client.start_compress_mkv())


def test_ffprobe_duration(tmp_path):
    test_mkv = get_large_test_file()
    output_path = tmp_path / test_mkv.name
    client = FFmpegClient(input_path=test_mkv, output_path=output_path, source_type="DVD")
    correct_duration = 147.213733333
    ffprobe_info = client.get_ffprobe_info()
    returned_duration = ffprobe_info["duration"]
    assert correct_duration == returned_duration


def test_ffprobe_field_order(tmp_path):
    test_mkv = get_large_test_file()
    output_path = tmp_path / test_mkv.name
    client = FFmpegClient(input_path=test_mkv, output_path=output_path, source_type="DVD")
    ffprobe_info = client.get_ffprobe_info()
    returned_field_order = ffprobe_info["field_order"]
    assert returned_field_order == "progressive"


# This test may take a couple minutes
@pytest.mark.slow
def test_compress_mkv(tmp_path):
    test_mkv = get_large_test_file()
    output = tmp_path / "test-small-mkv.mkv"
    client = FFmpegClient(input_path=test_mkv, output_path=output, source_type="DVD")
    deque(client.start_compress_mkv(), maxlen=0)
