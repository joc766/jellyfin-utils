import datetime
from collections import deque
from pathlib import Path

import boto3
import pytest
from botocore import UNSIGNED
from botocore.config import Config

from media_tools.ffmpeg_tool.client import FFmpegClient


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
        client = FFmpegClient(input_path=dummy_input)
        # iterate through generator
        list(client.start_compress_mkv(output_path=test_path, overwrite=False))


def test_file_not_exists(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        dummy_input = tmp_path / "input.mkv"
        test_path = tmp_path / "existing_file.mp4"
        client = FFmpegClient(input_path=dummy_input)
        # iterate through generator
        list(client.start_compress_mkv(output_path=test_path))


def test_ffprobe_duration():
    test_mkv = get_large_test_file()
    client = FFmpegClient(input_path=test_mkv, source_type="DVD")
    correct_duration = datetime.timedelta(seconds=147, microseconds=213733)
    ffprobe_info = probe_video(client.input_path)
    returned_duration = ffprobe_info.tags.duration_eng
    assert correct_duration == returned_duration


def test_ffprobe_field_order():
    test_mkv = get_large_test_file()
    client = FFmpegClient(input_path=test_mkv, source_type="DVD")
    ffprobe_info = probe_video(client.input_path)
    returned_field_order = ffprobe_info.field_order
    assert returned_field_order == "progressive"


def test_compress_interrupt(tmp_path):
    test_mkv = get_large_test_file()
    output_path = tmp_path / "test-small-mkv.mkv"
    client = FFmpegClient(input_path=test_mkv, source_type="DVD")
    with pytest.raises(InterruptedError):
        generator = client.start_compress_mkv(output_path=output_path)
        next(generator)
        generator.throw(KeyboardInterrupt)


# This test may take a couple minutes
@pytest.mark.slow
def test_compress_mkv(tmp_path):
    test_mkv = get_large_test_file()
    output_path = tmp_path / "test-small-mkv.mkv"
    client = FFmpegClient(input_path=test_mkv, source_type="DVD")
    deque(client.start_compress_mkv(output_path=output_path), maxlen=0)
